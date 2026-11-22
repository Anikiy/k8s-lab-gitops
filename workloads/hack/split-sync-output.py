#!/usr/bin/env python3
import json, sys, pathlib, yaml   # sudo apt install python3-yaml

src, rules_out, dash_dir = sys.argv[1:4]
uid = sys.argv[4] if len(sys.argv) > 4 else None
DS = {"type": "prometheus", "uid": uid}
dash = pathlib.Path(dash_dir); dash.mkdir(parents=True, exist_ok=True)

def fix(o):
    if isinstance(o, dict):
        for k, v in list(o.items()):
            if k != "datasource":
                fix(v); continue
            if v is None:
                o[k] = DS
            elif isinstance(v, str):
                if v in ("VictoriaMetrics", "prometheus", "default") or v.startswith("${DS"):
                    o[k] = DS
            elif isinstance(v, dict):
                if v.get("uid") == "grafana" or v.get("type") == "datasource":
                    continue                      # Mixed / built-in — не трогаем
                if v.get("uid") != uid:
                    o[k] = DS
    elif isinstance(o, list):
        for i in o: fix(i)

rules = []
for d in yaml.safe_load_all(open(src)):
    if not d: continue
    if d.get("kind") == "VMRule":
        rules.append(d)
    elif d.get("kind") == "ConfigMap" and \
         d.get("metadata", {}).get("labels", {}).get("grafana_dashboard") == "1":
        for key, val in (d.get("data") or {}).items():
            j = json.loads(val)
            j.pop("__inputs", None)
            if uid:
                fix(j)
                for v in j.get("templating", {}).get("list", []):
                    if v.get("type") == "datasource":
                        v["current"] = {"selected": True, "text": "VictoriaMetrics", "value": uid}
            name = pathlib.Path(key).stem or d["metadata"]["name"]
            (dash / f"{name}.json").write_text(json.dumps(j, indent=2))
            print("dashboard:", name)

with open(rules_out, "w") as f:
    yaml.safe_dump_all(rules, f, sort_keys=False)
print("VMRules:", len(rules))