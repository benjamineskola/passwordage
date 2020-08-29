#!/usr/bin/env python
import datetime
import json
import os
import subprocess
import sys

now = datetime.datetime.now()
ts = int(now.timestamp())


def load_data(uuid=None):
    if uuid:
        command = ["op", "get", "item", uuid]
    else:
        command = ["op", "list", "items"]

    return json.loads(subprocess.run(command, stdout=subprocess.PIPE).stdout)


def process_item(item: dict):
    if item["templateUuid"] != "001":
        return

    password_time = datetime.datetime.strptime(item["createdAt"], "%Y-%m-%dT%H:%M:%SZ")

    if now - password_time > datetime.timedelta(days=365):
        # don't bother checking password history if they're less than a year old
        full_item = load_data(item["uuid"])

        if (
            "passwordHistory" in full_item["details"]
            and full_item["details"]["passwordHistory"]
        ):
            # item has more than one password
            newest_password = max(
                [p["time"] for p in full_item["details"]["passwordHistory"]]
            )
            password_time = datetime.datetime.fromtimestamp(newest_password)

    if "ainfo" in item["overview"]:
        if "tags" not in item["overview"]:
            item["overview"]["tags"] = []
        return {
            "site": item["overview"]["title"],
            "date": password_time.timestamp(),
            "userid": item["overview"]["ainfo"],
            "tags": item["overview"]["tags"],
        }
    else:
        print(f"No ainfo for {full_item['overview']['title']}", file=sys.stderr)


def main():
    if not "XDG_CACHE_HOME" in os.environ:
        os.environ["XDG_CACHE_HOME"] = os.path.join(os.environ["HOME"], ".cache")
    cachefile = os.path.join(
        os.environ["XDG_CACHE_HOME"], "passwordage", "passwords.json"
    )

    if os.path.isfile(cachefile) and (
        (os.stat(cachefile).st_mtime - ts) < (60 * 60 * 24)
    ):
        results = json.load(open(cachefile))
    else:
        data = load_data()

        results = [process_item(i) for i in data]
        results = [i for i in results if i]

        results.sort(key=lambda k: k["date"])
        json.dump(results, open(cachefile, "w"))

    for login in results:
        if "todelete" in login["tags"]:
            continue

        date = datetime.datetime.fromtimestamp(login["date"])

        print(login["site"], end="")
        site_logins = [
            i for i in results if i["site"].casefold() == login["site"].casefold()
        ]

        if len(site_logins) > 1:
            print(f" ({login['userid']})", end="")
        print(f": {date} ({now - date})")


if __name__ == "__main__":
    main()
