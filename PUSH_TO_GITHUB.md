# Push this project to GitHub

Follow these steps to publish **only** this bot (not your whole home folder) as a new GitHub repo.

## 1. Create a new repo on GitHub

1. Go to [github.com/new](https://github.com/new).
2. **Repository name:** e.g. `automated-cv-submissions`.
3. **Description:** e.g. "Automated job application bot for Afghan job portals and LinkedIn".
4. Choose **Public**.
5. **Do not** check "Add a README" (you already have one).
6. Click **Create repository**.

## 2. Initialize Git in this folder and push

Open a terminal, go to this project folder, then run:

```bash
cd /Users/saeedahmadmalakzai/automated-cv-submissions

# Make this folder its own Git repo (only this project)
git init

# Confirm .env is ignored (should print a .gitignore line)
git check-ignore -v .env

# Stage everything ( .env, data/, logs/ are ignored)
git add .

# See what will be committed (no .env, no data/)
git status

# First commit
git commit -m "Initial commit: automated CV submission bot"

# Add your GitHub repo as remote (replace YOUR_USERNAME and REPO_NAME with yours)
git remote add origin https://github.com/YOUR_USERNAME/automated-cv-submissions.git

# Or if you use SSH:
# git remote add origin git@github.com:YOUR_USERNAME/automated-cv-submissions.git

# Push (set upstream branch)
git branch -M main
git push -u origin main
```

## 3. Before pushing: double-check

- Run `git status` and make sure **`.env` does not appear** in the list of files to be committed.
- If `.env` appears, **do not commit**. Run `git reset HEAD .env` and confirm `.env` is in `.gitignore`.

## 4. After the first push

- You can remove this file if you want: `rm PUSH_TO_GITHUB.md`
- To update the repo later: `git add .` → `git commit -m "Your message"` → `git push`
