# Multi-Agent Development Rules

This is the permanent repository-level rulebook for all AI coding agents working in this repository, including OpenAI Codex/Work and Google Antigravity.

---

## Golden Rule

> **NEVER ASSUME AN UNCOMMITTED CHANGE IS YOURS.**
> Never assume unexplained uncommitted changes belong to the current agent. If another agent appears to have unfinished work, stop rather than overwrite, stash, reset, clean, commit, or modify it.

---

## Core Rules

### 1. Ownership and Git State
- **Always inspect Git status, current branch, and recent commits** before starting development.
- **Never assume unexplained uncommitted changes belong to the current agent.**
- **If another agent appears to have unfinished work, stop** rather than overwrite, stash, reset, clean, commit, or modify it.
- **Only one agent should actively own a feature/task at a time.**
- **Feature work should normally happen on feature branches.**
- **`main` is stable.** Do not modify, merge into, reset, force-push, or otherwise alter `main` without Andy's explicit approval.
- **New development should normally start from a clean, synchronized Git handover point.**
- **Never overwrite another agent's unfinished work.**

### 2. Pre-Handover Checklist
Before handing work to another agent or completing a task:
- Run appropriate tests.
- Inspect the diff.
- Update relevant status/handover documentation.
- Commit coherent work.
- Push the feature branch.
- Verify Git state.

### 3. AI & Agent Usage Frugality
- **Be frugal with AI/agent usage.**
- **Prefer targeted file inspection and targeted tests** over repeated whole-repository scanning.
- **Do not repeat research or investigation** that is already documented.
- **Batch sensible changes** before running broader test suites.
- **For small administrative or straightforward tasks, if no observable progress has been made for approximately 10 minutes, stop and report what is blocking progress rather than repeatedly retrying or continuing to reason indefinitely.**
- **If usage runs out mid-task**, leave the repository in the safest coherent state possible and update handover documentation.

### 4. External Services & Paid Generation
- **Do not perform live paid or potentially paid OpenAI, Modal, ACE-Step, image, audio, or future video generation without explicit approval.**
- **Automated tests must mock paid/external generation.**

### 5. Security & Artifact Hygiene
- **Never expose, print, commit, or move `.env` values or credentials into client-side code.**
- **Never weaken TLS or other security controls to make something work.**
- **Do not commit generated audio, images, model weights, caches, virtual environments, or temporary runtime data** unless explicitly documented.

---

## Agent Workflows

### STARTING WORK
1. Run `git status`, verify the current branch, and review recent commits.
2. Read `CURRENT_WORK.md` and any referenced handover document.
3. Verify the working tree is clean BEFORE claiming ownership:
   - If uncommitted changes exist that you did not create, **STOP immediately**. Do not overwrite, stash, reset, clean, or commit them. Report the state to Andy.
   - Confirm `STATUS` in `CURRENT_WORK.md` is `READY` (or explicitly assigned to your agent).
4. After confirming the repository is clean and available, update `CURRENT_WORK.md` to `STATUS: ACTIVE` and `OWNER: <agent>`. That ownership change is then an expected modification belonging to the current agent and should not cause it to stop itself.

### DURING WORK
1. Work strictly on the designated feature branch.
2. Use targeted file reads and edits; do not touch unrelated code.
3. Ensure automated tests mock any external or paid services.
4. Batch changes logically and run targeted tests to verify work.

### FINISHING / HANDOVER
1. Run appropriate test suites to confirm correctness without regressions.
2. Run `git diff` and `git status` to verify all changes are clean and intentional.
3. Update handover documentation and set `STATUS` in `CURRENT_WORK.md` to `READY` (or `REVIEW` if awaiting Andy's review/approval).
4. Commit coherent work with a clear, informative commit message.
5. Push the feature branch to the remote repository.
6. Verify Git state is clean and synchronized.

### BLOCKED / USAGE EXHAUSTED
1. Halt active modifications immediately.
2. Do not discard or overwrite partial work if it can be safely retained.
3. Update `CURRENT_WORK.md`:
   - Set `STATUS: BLOCKED`.
   - Maintain your agent name as `OWNER`.
   - Document the blocker, partial state, and next steps in `CURRENT_WORK.md` or a handover document.
4. Leave the working tree in the safest possible coherent state and notify Andy.
