---
name: The documentation is wrong or unclear
about: A README, guide or help text that says something bonewright does not do, a broken command or link, a missing step
labels: documentation
---

**Where.** The file and the heading or line, e.g. `docs/GUIDE.md` → "Settings (`runs/config.json`)", or the
`--help` text of a `bw` command. A link to the line on GitHub is best.

**What it says.** Quote the sentence, command or number.

**What actually happens.** What you ran and what you saw instead (the output, or the file it produced). If it is
not wrong but hard to follow, say which step lost you.

**Version.** The output of `bw --version`, or the commit you were reading on GitHub.

A wrong number or default is worth reporting even if you are not sure — several have been found this way. A small
fix can go straight to a pull request instead; see CONTRIBUTING.md.
