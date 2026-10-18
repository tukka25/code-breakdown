# Breaking down a pull request or a branch

The canvas shows the changed code in call order, with its unchanged neighbours dimmed.

- Changed lines get a `+` gutter.
- Lines a change removed or replaced appear in place, marked `−`, cut from the base version.
- Boxes are marked new, changed or deleted.
- The author's own words sit in an "Author's claim" panel. For a GitHub PR, that is its title and description. For a branch with no PR, it is the branch's commit messages.

You never summarise the change yourself; the render quotes the author's text exactly.

## 1. Name the two sides

- **A GitHub PR:**

  ```
  gh pr view 42 --json number,title,url,baseRefName,headRefName,baseRefOid,headRefOid,files
  ```

  Use `baseRefOid` as `base` and `headRefOid` as `head`. If the head commit is not in the local repository, fetch it with `git fetch origin pull/42/head`.
- **A branch with no PR:** `base` is the branch it goes into (often `main` or `origin/main`), and `head` is the branch. Branch names work; so do commit shas.

**Always set `head` unless the change is in the working tree you have checked out.** Without `head`, every block is read from the working tree, which may be the base branch.

## 2. See what changed

```
git diff --stat <base>...<head>
git diff -U0 <base>...<head> -- <file>
```

## 3. Read the head version with line numbers

Line numbers in the spec come from the head version. When the head branch is checked out, read the files directly. Otherwise print a file at the head with line numbers, without checking anything out:

```
git grep -n -e '' <head> -- <file>
```

Each line comes out as `<head>:<file>:<number>:<text>`.

Deleted declarations take their line numbers from the merge base. Get it with `git merge-base <base> <head>`, then run `git grep -n -e '' <merge-base> -- <file>`.

## 4. Choose blocks

For a change, these rules come before the general trimming order in SKILL.md:

- **Entry:** where the change starts. That is the highest changed function on each call path, such as a route handler or a public method. Two unrelated changes become two entries.
- **Changed and new declarations** along those paths: functions, methods, and types whose fields changed. Never leave one out for space, not even a new exception class.
- **Unchanged neighbours a reader needs:** the caller that leads into a changed function, the callee whose behaviour the change relies on, and the types a changed line reads or writes. They show dimmed.
- **Deleted declarations:** blocks with `"side": "base"`, using line numbers from the merge base. An arrow can point at one from the removed line that called it.
- **Trimming:** if that is more than about 16 blocks, trim only unchanged neighbours, in SKILL.md's order, and name them in the reply.

## 5. Write the spec

```json
{
  "kind": "pr",
  "title": "PR #42: Add coupon support",
  "pr": 42,
  "base": "<baseRefOid>",
  "head": "<headRefOid>",
  "entry": ["create_order"],
  "blocks": [],
  "edges": []
}
```

The `blocks` and `edges` arrays are filled in as for any other spec.

- **For a branch with no PR,** leave out `pr` and use a title like `feature/coupons vs main`.
- **Then check and render as usual.** If `gh` cannot read the PR, the render still works; it warns that the canvas has no author's claim.
