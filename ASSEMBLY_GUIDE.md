# Assembly Guide (delete this file before publishing)

Everything in this repo skeleton was generated from the code and decisions worked out during development, but two things need to come from **your actual Colab session**, not from here, before this is ready to publish:

## 1. Replace the notebooks with your executed versions

The `.ipynb` files in `notebooks/` right now contain only code and markdown — no run outputs, because they were built and syntax-checked, but never actually executed against the real Materials Project data (that only happened in your Colab sessions). For a portfolio repo, viewers should be able to see the printed tables and inline plots without re-running anything.

For each notebook, in Colab:
1. Open the corresponding session (or re-run it fresh if the runtime has reset)
2. File → Download → Download .ipynb
3. Replace the matching file in `notebooks/` with the downloaded one (same filename)

## 2. Add the figure files

Copy the PNGs from `MyDrive/materials_bandgap_project/figures/` into this repo's `figures/` folder — see `figures/README.md` for the exact list.

## 3. Publish

```bash
cd <this-repo-folder>
git init
git add .
git commit -m "Initial commit: band gap prediction from composition and structure"
git branch -M main
git remote add origin <your-github-repo-url>
git push -u origin main
```

## 4. Optional: embed key figures in the README

Once figures are in place, you can add inline images to the main `README.md`, e.g.:

```markdown
![Parity plot](figures/fig_stage7_parity_selected_model.png)
```

The parity plot and the bias-by-band-gap-bin plot are the two most informative figures for a reader skimming the README — worth featuring prominently.

---

*Delete this file once the above steps are done — it's a checklist for you, not part of the finished repo.*
