"""What a template asks of the host, read from compose's OWN resolved model.

For the job summary the signer reads before approving: each template's compose is resolved with
`docker compose config --format json` (anchors, merge keys, `extends` and interpolation already
applied, so YAML spelling cannot hide a feature), with fixed dummy values and a clean
environment, and the host-facing features are listed. The summary shows the DELTA against the
deployed catalogue, so a template that quietly gains `privileged` or a Docker socket stands out.

Nothing is pulled or started: `config` only parses. Only templates that already pass the sanity
rules are resolved (so a refused `include:` is never fetched). The values used are dummies: the
template's own default when it has one, else `dummy` (secrets `dummy-secret`). They reach compose
through `--env-file` (single-quoted, so taken literally), never through the process environment,
which holds only PATH and a scratch HOME: a template variable named LD_PRELOAD or DOCKER_HOST
must not configure the compose process itself, and the runner's variables cannot leak in. Keys
compose or the CLI read to configure themselves (COMPOSE_*, DOCKER_* and the other reserved names)
are left out of the env file.
"""
import json
import os
import subprocess
import tempfile

import catalog_sanity as sanity

SOCKETS = ("docker.sock", "podman.sock", "containerd.sock", "crio.sock")
SENSITIVE_ROOTS = ("/", "/etc", "/root", "/home", "/var/lib", "/var/run", "/run", "/proc", "/sys", "/dev",
                   "/boot", "/usr", "/lib", "/var/log")
STRONG_CAPS = {"ALL", "SYS_ADMIN", "NET_ADMIN", "SYS_PTRACE", "SYS_MODULE", "DAC_READ_SEARCH", "SYS_RAWIO"}


class ResolveError(Exception):
    pass


def dummy_values(template):
    values = {}
    for variable in template["variables"]:
        credential = variable.get("credential") or {}
        secret = variable["isSecret"] or credential.get("field") == "password" or "generate" in variable
        if variable["defaultValue"]:
            values[variable["key"]] = variable["defaultValue"]
        else:
            values[variable["key"]] = "dummy-secret" if secret else "dummy"
    return values


def env_file_text(values):
    """The dummies as an env file compose reads literally. A key that is not an environment name, or
    that compose or the CLI read to configure themselves, is left out (the placeholder then resolves
    empty, which the sanity gates already refuse for a template being published); a value that
    single quotes cannot carry is refused rather than guessed."""
    lines = []
    for key, value in values.items():
        if not sanity.is_env_name(key) or sanity.is_reserved_key(key):
            continue
        if "'" in value or any(ch in value for ch in "\r\n\0"):
            raise ResolveError(f"the value of {key} cannot be passed to compose literally (a quote or a line break)")
        lines.append(f"{key}='{value}'")
    return "".join(line + "\n" for line in lines)


# Keys that make `compose config` READ a file on the machine it runs on. Not resolved on the runner:
# a template could otherwise name a runner file and have a parse error quote it into the public
# log or summary. Plain text search is enough because the refusals (run first) reject the numeric
# escapes that could spell a key without its letters.
HOST_FILE_KEYS = ("env_file", "label_file")


def resolve(template, compose_cmd=("docker", "compose"), timeout=60):
    """The resolved model (dict) and the project directory it was resolved in."""
    for key in HOST_FILE_KEYS:
        if key in template["compose"]:
            raise ResolveError(f"uses {key}, which reads a host file: not resolved on the runner, review it by hand")
    with tempfile.TemporaryDirectory(prefix="catalog-risk-") as root:
        project = os.path.join(root, "stack")
        os.mkdir(project)
        path = os.path.join(project, "compose.yaml")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(template["compose"])
        env_file = os.path.join(root, "dummy.env")
        with open(env_file, "w", encoding="utf-8") as handle:
            handle.write(env_file_text(dummy_values(template)))
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": root}
        try:
            result = subprocess.run(
                list(compose_cmd) + ["--env-file", env_file, "--project-directory", project, "-p", "catalog-check",
                                     "-f", path, "config", "--format", "json"],
                cwd=project, env=env, capture_output=True, text=True, timeout=timeout)
        except FileNotFoundError:
            raise ResolveError("docker compose is not installed") from None
        except subprocess.TimeoutExpired:
            raise ResolveError("docker compose config timed out") from None
        if result.returncode != 0:
            tail = (result.stderr.strip().splitlines() or ["(no output)"])[-1]
            raise ResolveError(f"docker compose config failed: {tail[:300]}")
        try:
            return json.loads(result.stdout), project
        except ValueError:
            raise ResolveError("docker compose config did not print JSON") from None


def _host_path(source, project):
    """A bind source as the summary shows it: `./x` inside the stack folder, `../x` climbing out."""
    if source == project or source.startswith(project + "/"):
        return "." + source[len(project):]
    parent = os.path.dirname(project)
    if source == parent or source.startswith(parent + "/"):
        return "../" + os.path.relpath(source, parent) + "  (outside the stack folder)"
    return source


def _sensitive(source):
    return any(source == root or source.startswith(root.rstrip("/") + "/") for root in SENSITIVE_ROOTS if root != "/")


def features(model, project):
    """A set of (text, strong) pairs: one per host-facing feature."""
    out = set()

    def add(text, strong=False):
        out.add((text, strong))

    for name, service in sorted((model.get("services") or {}).items()):
        prefix = f"{name}:"
        if service.get("privileged"):
            add(f"{prefix} privileged", True)
        for cap in service.get("cap_add") or []:
            add(f"{prefix} cap_add {cap}", cap.upper().removeprefix("CAP_") in STRONG_CAPS)
        for device in service.get("devices") or []:
            source = device.get("source") if isinstance(device, dict) else str(device).split(":")[0]
            add(f"{prefix} device {source}", True)
        for rule in service.get("device_cgroup_rules") or []:
            add(f"{prefix} device_cgroup_rules {rule}", True)
        for opt in service.get("security_opt") or []:
            add(f"{prefix} security_opt {opt}", "unconfined" in opt or "disable" in opt)
        mode = service.get("network_mode")
        if mode and (mode == "host" or mode.startswith("container:")):
            add(f"{prefix} network_mode {mode}", mode == "host")
        for key in ("pid", "ipc", "uts", "userns_mode", "cgroup"):
            if service.get(key):
                add(f"{prefix} {key} {service[key]}", service[key] == "host")
        if service.get("use_api_socket"):
            add(f"{prefix} use_api_socket (the container-engine socket, without a bind mount)", True)
        provider = service.get("provider")
        if provider:
            kind = provider.get("type") if isinstance(provider, dict) else provider
            add(f"{prefix} provider {kind} (runs a host-side plugin instead of a container)", True)
        build = service.get("build")
        if build:
            build = build if isinstance(build, dict) else {"context": build}
            context = str(build.get("context", ""))
            remote = "://" in context or context.startswith("git@")
            shown = context if remote else _host_path(context, project)
            add(f"{prefix} builds an image on the host from {shown}", remote or "(outside" in shown)
            if build.get("ssh"):
                add(f"{prefix} build ssh {build['ssh']} (forwards the host's SSH agent or keys)", True)
            for secret in build.get("secrets") or []:
                source = secret.get("source") if isinstance(secret, dict) else secret
                add(f"{prefix} build secret {source}", True)
            for name, ctx in sorted((build.get("additional_contexts") or {}).items()):
                add(f"{prefix} build context {name} {ctx}", True)
        if service.get("cgroup_parent"):
            add(f"{prefix} cgroup_parent {service['cgroup_parent']}", True)
        for other in service.get("volumes_from") or []:
            add(f"{prefix} volumes_from {other}")
        for key in sorted((service.get("sysctls") or {})):
            add(f"{prefix} sysctl {key}")
        for env_file in service.get("env_file") or []:
            path = env_file.get("path") if isinstance(env_file, dict) else env_file
            add(f"{prefix} env_file {_host_path(str(path), project)}", True)
        for volume in service.get("volumes") or []:
            if volume.get("type") != "bind":
                continue
            source = volume.get("source", "")
            shown = _host_path(source, project)
            read_only = bool(volume.get("read_only"))
            socket = source.endswith(SOCKETS)
            strong = socket or source == "/" or "(outside" in shown or (_sensitive(source) and not read_only)
            label = "container-engine socket" if socket else "host path"
            add(f"{prefix} {label} {shown} -> {volume.get('target')}{' (read-only)' if read_only else ''}", strong)
        for port in service.get("ports") or []:
            host_ip = port.get("host_ip") or ""
            published = port.get("published")
            if not published:
                continue
            where = "all interfaces" if host_ip in ("", "0.0.0.0", "::") else host_ip
            add(f"{prefix} port {published}/{port.get('protocol', 'tcp')} on {where}")
    for name, volume in sorted((model.get("volumes") or {}).items()):
        options = (volume or {}).get("driver_opts") or {}
        if options.get("device"):
            add(f"volume {name}: driver_opts device {options['device']}", True)
    for block in ("secrets", "configs"):
        for name, item in sorted((model.get(block) or {}).items()):
            item = item or {}
            if item.get("file"):
                add(f"{block[:-1]} {name}: reads host file {_host_path(item['file'], project)}", True)
            if item.get("environment"):
                add(f"{block[:-1]} {name}: reads host environment {item['environment']}", True)
    return out


def template_features(template, compose_cmd=("docker", "compose")):
    model, project = resolve(template, compose_cmd)
    return features(model, project)
