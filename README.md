# [iterm2-bettergit](https://github.com/djpadz/iterm2-bettergit)

_An enhanced git status bar widget for iTerm2_

## Features
- Displays the following information in the iTerm2 status bar:
    - Quick indicator of the current branch status:
      - `🟢` Branch is clean
      - `🌕` Branch is in sync, but there are pulls and/or pushes available.
      - `🔴` Branch is out of sync, and/or there are uncommited changes.
    - Current branch name
    - `⬆︎` Number of commits ahead of the remote
    - `⬇`︎ Number of commits behind the remote
    - `✎`︎ Number of unstaged changed files
    - `⚠︎` Number of untracked files
    - `−` Number of unstaged deleted files
    - `✓` Number of staged files
    - `⮹`️ Number of stashes
- Also has a special mode for rebasing, merging, cherry-picking, reversion, or bisection.

## Installation
1. Download the latest release from the [releases page].
2. Double-click it to install it in iTerm2. Tell it to autolaunch.
3. You will need to add the following to your `~/.bash_profile` or `~/.zshrc`:
    ```bash
    iterm2_print_user_vars()
    {
        iterm2_set_user_var python_bettergit_cwd "${PWD}"
        iterm2_set_user_var python_bettergit_random "${RANDOM}"
    }
    ```
   If you have an existing `iterm2_print_user_vars()` function, then just add the body of the function above to the body of yours.
