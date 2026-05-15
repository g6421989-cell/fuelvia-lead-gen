SESSION RULES — READ AND FOLLOW BEFORE DOING ANYTHING
======================================================

FIRST PRIORITY:
Read CLAUDE_INSTRUCTIONS.md and PROJECT_MEMORY.md
completely before touching any file or writing any code.
Confirm you have read them before starting.

CODE QUALITY RULES:
- Write production grade code only
- No shortcuts, no hacks, no lazy implementations
- Every function must be complete, not placeholder
- Every edge case must be handled
- Code must be clean, readable and scalable
- No "TODO" comments unless I specifically ask
- No half done logic — if you start something finish it

TOKEN SAVING RULES:
- Do not explain what you are about to do, just do it
- Do not summarize what you just did after doing it
- Do not add "I have successfully completed..." messages
- Do not repeat my question back to me
- Do not write long introductions before answering
- If I ask you to fix something, fix it — no essay before the fix
- Skip all filler phrases like "Great question", "Certainly",
  "Of course", "Happy to help" — just get to work
- Do not over comment code — only comment complex logic
- Do not explain basic code that is self explanatory

RESPONSE FORMAT:
- Code first, always
- If explanation is needed, after the code, keep it short
- Use bullet points not paragraphs for any explanation
- Maximum 5 lines of explanation unless I ask for more
- If I ask yes or no question — answer yes or no first
  then explain if needed

WHEN MAKING CHANGES:
- Only touch files relevant to the current task
- Do not refactor unrelated code without asking me
- Do not rename things without asking me
- Do not change working logic without asking me
- One task at a time — complete it fully before moving on

WHEN YOU ARE STUCK:
- Tell me in one line what the blocker is
- Give me two options to resolve it
- Do not write paragraphs about why something is hard

MEMORY UPDATE RULE:
- After every file created or modified append one line
  to PROJECT_MEMORY.md in this format:
  [ACTION] filename — what changed — status
- Do not rewrite PROJECT_MEMORY.md ever
- Only append new lines at the bottom

ERROR HANDLING RULE:
- If you find a bug while working on something else
  do not fix it silently
- Tell me in one line — found bug in X, should I fix now
  or log it for later
- Never silently change logic that was working before

CONFIRMATION BEFORE STARTING:
After reading all files reply with exactly this format
and nothing else:

PROJECT: [project name]
STAGE: [current completion percentage]
LAST COMPLETED: [last feature or task done]
CURRENT TASK: [what we are working on now]
READY: YES
