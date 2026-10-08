"""What a template asks of the host, read from compose's OWN resolved model.

For the job summary the signer reads before approving: each template's compose is resolved with
`docker compose config --format json` (anchors, merge keys, `extends` and interpolation already
applied, so YAML spelling cannot hide a feature), with fixed dummy values and a clean
environment, and the host-facing features are listed. The summary shows the DELTA against the
deployed catalogue, so a template that quietly gains `privileged` or a Docker socket stands out.

Nothing is pulled or started: `config` only parses. Only templates that already pass the sanity
rules are resolved (so a refused `include:` is never fetched). The values used are dummies: the
template's own default when it has one, else `dummy` (secrets `dummy-secret`). The process
environment is cleared except PATH, so the runner's variables cannot leak in.
"""
import json
import os
import subprocess
import tempfile

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


def resolve(template, compose_cmd=("docker", "compose"), timeout=60):
    """The resolved model (dict) and the project directory it was resolved in."""
    with tempfile.TemporaryDirectory(prefix="catalog-risk-") as root:
        project = os.path.join(root, "stack")
        os.mkdir(project)
        path = os.path.join(project, "compose.yaml")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(template["compose"])
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": root}
        env.update(dummy_values(template))
        try:
            result = subprocess.run(
                list(compose_cmd) + ["--project-directory", project, "-p", "catalog-check", "-f", path,
                                     "config", "--format", "json"],
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
