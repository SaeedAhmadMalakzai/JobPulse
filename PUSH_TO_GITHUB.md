# Push JobPulse to GitHub

## License

This project uses the **MIT License** (see [LICENSE](LICENSE)). It allows anyone to use, modify, and distribute the code with minimal restrictions. When you create the repo on GitHub, you can select **MIT** in the "Add a license" dropdown if you create the repo without a README; otherwise the existing `LICENSE` file in this repo will be pushed and GitHub will detect it.

---

## 1. Create the repo on GitHub

1. Go to **[github.com/new](https://github.com/new)**.
2. **Repository name:** `jobpulse` (or whatever you prefer).
3. **Description:** e.g. *JobPulse – Always scanning. Always applying. Automated job application bot for Afghan job portals and LinkedIn.*
4. Choose **Public**.
5. **Do not** check "Add a README" or "Add .gitignore" (this repo already has them).
6. **License:** Choose **MIT License** if the dropdown appears (or leave empty; the repo already contains a `LICENSE` file).
7. Click **Create repository**.

---

## 2. Add remote and push

Open a terminal in the project folder:

```bash
cd /Users/saeedahmadmalakzai/automated-cv-submissions

# If you haven’t committed the new LICENSE yet:
git add LICENSE
git add -u
git status
git commit -m "Add MIT license"

# Add your GitHub repo (replace YOUR_USERNAME with your GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/jobpulse.git

# Push
git push -u origin main
```

If you already added `origin` before, use:

```bash
git remote set-url origin https://github.com/YOUR_USERNAME/jobpulse.git
git push -u origin main
```

**Using SSH instead of HTTPS:**

```bash
git remote add origin git@github.com:YOUR_USERNAME/jobpulse.git
git push -u origin main
```

---

## 3. Safety check before push

- Run `git status` and confirm **`.env` does not appear** in the list.
- If `.env` is listed, **do not push**. Run `git reset HEAD .env` and ensure `.env` is in `.gitignore`.

---

## 4. After pushing

- Later updates: `git add .` → `git commit -m "Your message"` → `git push`
- To change the license in the future, edit `LICENSE` and push again.
