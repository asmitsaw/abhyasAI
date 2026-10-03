# AbhyasAI Hackathon --- Team Merge & Integration Protocol

> **Purpose:** Allow multiple teammates to work on different pages,
> APIs, services, UI components, AI/RAG modules, and fixes at the same
> time while minimizing merge conflicts and making final integration
> predictable.
>
> **Rule #1:** Nobody directly works on or force-pushes `main`.
>
> **Rule #2:** Each person owns a clearly defined area and works in a
> separate branch.
>
> **Rule #3:** Merge small, focused changes frequently instead of
> combining a huge amount of work at the end.

------------------------------------------------------------------------

## 1. Repository Branch Structure

Use this structure:

``` text
main
│
├── feat/<name>-<feature>
├── fix/<name>-<issue>
├── ui/<name>-<page>
├── api/<name>-<api>
├── rag/<name>-<rag-work>
├── ai/<name>-<ai-work>
├── db/<name>-<database-work>
└── docs/<name>-<docs-work>
```

Examples:

``` text
feat/rahul-adaptive-quiz
ui/priya-dashboard
rag/aman-citations
api/neha-viva
fix/arjun-login
docs/team-architecture
```

### Never use

``` text
final
final2
new
new-final
my-branch
testing
hackathon-final
```

Branches must describe the actual work.

------------------------------------------------------------------------

# 2. Golden Rule: One Person = One Ownership Area

Before starting work, claim an area.

Example:

  Team Member   Ownership
  ------------- --------------------
  Person A      Dashboard UI
  Person B      Adaptive Quiz
  Person C      RAG
  Person D      Viva
  Person E      Backend APIs
  Person F      Database
  Person G      Demo / Integration

Avoid having two people edit the same core file unnecessarily.

If two features require the same file, coordinate BEFORE editing it.

------------------------------------------------------------------------

# 3. Protected Files

These files are high-conflict files.

Examples:

``` text
app.py
config.py
requirements.txt
package.json
README.md
database models
shared CSS
shared JS
main templates/layout files
API route registration
```

Do not casually modify these files.

If you need a change in one:

1.  Tell the team.
2.  Make the smallest possible change.
3.  Commit it separately.
4.  Inform everyone before merging.

------------------------------------------------------------------------

# 4. Work Isolation

Every developer should start from an updated `main`.

``` bash
git switch main
git pull origin main
git switch -c feat/<your-name>-<feature>
```

Example:

``` bash
git switch main
git pull origin main
git switch -c feat/rahul-adaptive-quiz
```

------------------------------------------------------------------------

# 5. Never Work Directly on Main

Do NOT do this:

``` bash
git switch main
# edit files
git add .
git commit
git push origin main
```

Instead:

``` bash
git switch -c feat/<name>-<feature>
```

Push your branch:

``` bash
git push -u origin feat/<name>-<feature>
```

Then create a Pull Request into `main`.

------------------------------------------------------------------------

# 6. Commit Rules

Keep commits small and meaningful.

### Good

``` text
feat: add adaptive quiz API
feat: add dashboard mastery card
fix: handle missing transcript
refactor: isolate RAG citation builder
test: add adaptive quiz tests
docs: update API documentation
```

### Bad

``` text
changes
update
final
working
done
hackathon
everything
```

One commit should ideally represent one logical change.

------------------------------------------------------------------------

# 7. The Most Important Hackathon Rule

## Do NOT commit generated junk.

Never commit:

``` text
.env
__pycache__/
*.pyc
node_modules/
.venv/
venv/
dist/
build/
coverage/
.DS_Store
IDE temporary files
local databases
API keys
secrets
large generated files
```

Make sure `.gitignore` contains appropriate entries.

------------------------------------------------------------------------

# 8. Environment Variables

Never commit API keys.

Use:

``` text
.env
```

locally.

Commit:

``` text
.env.example
```

instead.

Example:

``` env
GEMINI_API_KEY=
CHROMA_API_KEY=
CHROMA_TENANT=
CHROMA_DATABASE=
```

Each teammate creates their own `.env`.

NEVER:

``` python
GEMINI_API_KEY = "actual-secret-key"
```

------------------------------------------------------------------------

# 9. Before Starting Work

Every developer should run:

``` bash
git switch main
git pull origin main
git switch <your-branch>
```

Then update their branch:

``` bash
git merge main
```

or, if the team explicitly agrees to use rebase:

``` bash
git rebase main
```

### Team recommendation

For a hackathon, prefer:

``` bash
git merge main
```

because it is easier for less experienced teammates and avoids rewriting
shared history.

------------------------------------------------------------------------

# 10. Before Pushing

Run:

``` bash
git status
git diff
```

Then run the project's tests.

For Python:

``` bash
pytest
```

If available:

``` bash
python -m compileall .
```

If the project has frontend checks, run those too.

Only push code that you have actually tested.

------------------------------------------------------------------------

# 11. Before Creating a Pull Request

Run:

``` bash
git fetch origin
git merge origin/main
```

Resolve conflicts locally.

Then:

``` bash
pytest
```

If everything passes:

``` bash
git push
```

Then create the Pull Request.

------------------------------------------------------------------------

# 12. Pull Request Rules

Every PR must contain:

``` text
WHAT:
What did you build/fix?

FILES:
Which important files changed?

TESTED:
What did you run?

DEPENDENCIES:
Does another feature depend on this?

CONFLICT RISK:
Did you touch shared/core files?

DEMO:
How can the team quickly verify it?
```

Example:

``` text
WHAT:
Added adaptive quiz generation based on mastery.

FILES:
services/adaptive_quiz.py
routes/quiz.py
templates/quiz.html

TESTED:
pytest tests/test_adaptive_quiz.py

DEPENDENCIES:
Requires mastery service.

CONFLICT RISK:
quiz.html changed.

DEMO:
Open /quiz and select Operating Systems.
```

------------------------------------------------------------------------

# 13. Merge Order

When multiple features depend on each other, merge in dependency order.

Example:

``` text
Database
   ↓
Backend service
   ↓
API
   ↓
Frontend
   ↓
Integration
```

For AbhyasAI:

``` text
Database / Models
        ↓
Core Services
        ↓
RAG / AI Services
        ↓
API Routes
        ↓
Frontend Pages
        ↓
Dashboard / Integration
        ↓
Demo
```

Do not merge the UI first if its API does not exist unless the UI is
explicitly designed around a stable mock/interface.

------------------------------------------------------------------------

# 14. Feature Contracts

Before two teams connect their work, define the interface.

For an API, document:

``` text
Endpoint:
POST /api/adaptive-quiz

Request:
{
  "subject": "Operating Systems",
  "topic": "Deadlocks",
  "difficulty": "medium"
}

Response:
{
  "questions": [...]
}
```

The frontend team should integrate against the documented contract.

The backend team should avoid changing the response structure
unexpectedly.

If the contract changes:

1.  Announce it.
2.  Update documentation.
3.  Update tests.
4.  Update dependent code.

------------------------------------------------------------------------

# 15. Shared File Conflict Prevention

If you need to modify a shared file such as:

``` text
app.py
```

do not simultaneously restructure the entire file.

Instead:

``` text
BAD:
Rewrite app.py completely.

GOOD:
Add one route.
Add one import.
Keep existing structure unchanged.
```

The smaller the diff, the easier the merge.

------------------------------------------------------------------------

# 16. Avoid "Formatting Wars"

Do not reformat an entire file while adding one feature.

Bad:

``` text
Feature change: 10 lines
Formatting change: 800 lines
```

Good:

``` text
Feature change: 10–30 lines
Formatting change: 0 lines
```

This dramatically reduces merge conflicts.

------------------------------------------------------------------------

# 17. If You See a Conflict

Do NOT panic.

First:

``` bash
git status
```

Git will show conflicting files.

Open the file and look for:

``` text
<<<<<<< HEAD

your changes

=======

incoming changes

>>>>>>> main
```

Decide what the final code should contain.

Then remove the conflict markers.

After resolving:

``` bash
git add <resolved-file>
git commit
```

Run tests:

``` bash
pytest
```

Then push:

``` bash
git push
```

------------------------------------------------------------------------

# 18. Never Blindly Accept "Theirs" or "Ours"

Avoid doing this without understanding the file:

``` bash
git checkout --ours .
```

or:

``` bash
git checkout --theirs .
```

These can silently delete another teammate's work.

Always inspect the conflict first.

------------------------------------------------------------------------

# 19. Emergency Conflict Rule

If you cannot understand a conflict:

STOP.

Do not randomly edit it.

Do:

``` text
1. Save your branch.
2. Tell the owner of the conflicting area.
3. Show the conflicting file.
4. Resolve together.
5. Run tests.
```

A 5-minute discussion is cheaper than losing an hour of work.

------------------------------------------------------------------------

# 20. Shared Architecture Rule

The team must maintain one canonical architecture.

For AbhyasAI, keep the high-level flow consistent:

``` text
User
 ↓
Frontend
 ↓
API
 ↓
Application Services
 ↓
RAG / AI / Business Logic
 ↓
Database / Chroma Cloud / External APIs
```

Do not create duplicate implementations such as:

``` text
services/rag.py
services/new_rag.py
services/rag_final.py
services/rag2.py
```

Instead, improve the existing canonical service.

------------------------------------------------------------------------

# 21. Don't Create Duplicate Features

Before implementing a feature, search the repository.

Example:

``` bash
grep -R "adaptive" .
```

or use your IDE search.

Check:

``` text
Does this already exist?
Is someone else implementing it?
Is there already an API?
Is there already a service?
Is there already a UI component?
```

If yes, extend it instead of creating a second implementation.

------------------------------------------------------------------------

# 22. Stable Interfaces

Teams should communicate through stable interfaces.

Preferred:

``` text
services/
    adaptive_quiz.py
    mastery.py
    rag/
    viva.py
```

Routes call services:

``` text
route → service → database/AI
```

Avoid:

``` text
route → random helper → random database code → Gemini
```

Business logic should not be duplicated across frontend and backend.

------------------------------------------------------------------------

# 23. Frontend Ownership

Frontend developers should avoid editing backend logic.

Backend developers should avoid changing UI structure unless required.

Recommended ownership:

``` text
Frontend:
templates/
static/
components/

Backend:
routes/
services/
models/

RAG:
services/rag/

AI:
services/llm/
```

If a cross-layer change is required, coordinate it.

------------------------------------------------------------------------

# 24. Database Changes

Database/model changes are high-risk.

Before changing models:

``` text
ANNOUNCE:
"I am changing student_subjects and mastery schema."
```

Document:

``` text
Old:
student_subjects(...)

New:
student_subjects(...)
+ mastery_score
```

Run all database tests after changes.

Never silently change database fields that another teammate is using.

------------------------------------------------------------------------

# 25. RAG / AI Changes

For AbhyasAI, AI output should not silently break the rest of the
system.

If changing:

``` text
LLM provider
embedding model
Chroma schema
retriever
reranker
prompt structure
citation format
```

verify:

``` text
ingestion
→ embeddings
→ Chroma
→ retrieval
→ reranking
→ context
→ Gemini
→ citations
→ API
→ frontend
```

Run the relevant RAG tests before merging.

------------------------------------------------------------------------

# 26. Chroma Cloud Safety

Do not casually change:

``` text
collection names
metadata schema
embedding functions
dense index
sparse index
tenant
database
```

These are shared infrastructure.

If changing them, announce it first.

Example:

``` text
[RAG INFRA CHANGE]

Changing:
abhyas_syllabus

Reason:
Updated hybrid schema.

Impact:
All RAG developers.

Migration:
migrate_to_chroma_cloud.py

Rollback:
Use previous collection/schema.
```

------------------------------------------------------------------------

# 27. API Compatibility

When changing an existing endpoint:

### Prefer additive changes

Good:

``` json
{
  "score": 80,
  "mastery": 72
}
```

instead of suddenly changing:

``` json
{
  "result": 72
}
```

If a breaking change is unavoidable:

``` text
OLD:
GET /api/mastery

NEW:
GET /api/v2/mastery
```

or coordinate the frontend and backend changes in one integration PR.

------------------------------------------------------------------------

# 28. Integration Branch

For a large hackathon team, optionally maintain:

``` text
main
integration
```

Structure:

``` text
feature branches
      ↓
integration
      ↓
main
```

Use `integration` for combining multiple features before the final
stable merge.

Example:

``` bash
git switch integration
git pull origin integration

git merge feat/rahul-adaptive-quiz
git merge ui/priya-dashboard
git merge rag/aman-citations

pytest

git push origin integration
```

Once integration is stable:

``` text
integration → main
```

### IMPORTANT

Do not use `integration` as an excuse to skip testing.

------------------------------------------------------------------------

# 29. Recommended Hackathon Workflow

``` text
                    ┌─────────────────┐
                    │      MAIN       │
                    └────────┬────────┘
                             │
                  pull / branch from main
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
   Feature A             Feature B            Feature C
        │                    │                    │
        ▼                    ▼                    ▼
      PR A                 PR B                 PR C
        │                    │                    │
        └────────────────────┼────────────────────┘
                             ▼
                       INTEGRATION
                             │
                         run tests
                             │
                    manual demo testing
                             │
                             ▼
                           MAIN
```

------------------------------------------------------------------------

# 30. Integration Manager

During the final hackathon phase, assign ONE person as:

``` text
Integration Manager
```

Their job:

``` text
- monitor PRs
- check conflicts
- verify tests
- merge compatible features
- maintain integration branch
- run end-to-end demo
- prevent duplicate implementations
```

This person does NOT own everyone's code.

They own integration.

------------------------------------------------------------------------

# 31. Feature Freeze

When the hackathon enters the final phase, declare:

``` text
FEATURE FREEZE
```

After feature freeze:

### Allowed

``` text
bug fixes
UI polish
performance fixes
demo fixes
integration fixes
critical reliability fixes
```

### Avoid

``` text
new architecture
new database
new framework
new major feature
large refactor
embedding migration
massive UI rewrite
```

------------------------------------------------------------------------

# 32. Final 2-Hour Rule

In the final 2 hours:

``` text
NO MAJOR REFACTORING.
```

Do not:

``` text
change Flask architecture
replace Gemini
replace Chroma
rewrite frontend
rename 100 files
change database architecture
```

unless the existing system is completely broken.

Focus on:

``` text
stability
demo flow
bug fixes
UI polish
latency
error handling
presentation
```

------------------------------------------------------------------------

# 33. Daily Team Sync

At the start of a work session, every developer posts:

``` text
WORKING ON:
...

FILES:
...

DEPENDS ON:
...

I WILL MODIFY SHARED FILES:
YES / NO

EXPECTED DONE:
...
```

Example:

``` text
WORKING ON:
Adaptive quiz UI

FILES:
templates/quiz.html
static/quiz.js

DEPENDS ON:
POST /api/adaptive-quiz

I WILL MODIFY SHARED FILES:
NO

EXPECTED DONE:
45 minutes
```

------------------------------------------------------------------------

# 34. Before Merging: Integration Checklist

Every PR should satisfy:

``` text
[ ] Branch is updated with main/integration
[ ] No secrets committed
[ ] No unnecessary files changed
[ ] No duplicate implementation
[ ] Tests pass
[ ] Existing tests still pass
[ ] API contract documented
[ ] Database changes documented
[ ] Shared files reviewed
[ ] UI manually tested if applicable
[ ] RAG manually tested if applicable
[ ] No debug prints
[ ] No temporary code
[ ] No fake production data
[ ] No broken imports
[ ] No merge conflict markers
```

Search for conflict markers:

``` bash
git grep -n "<<<<<<<\|=======\|>>>>>>>"
```

This should return nothing before merge.

------------------------------------------------------------------------

# 35. Automated Pre-Commit Safety Check

Recommended local check:

``` bash
python -m compileall .
pytest
git grep -n "<<<<<<<\|=======\|>>>>>>>"
```

If all three succeed, the branch is much safer to merge.

------------------------------------------------------------------------

# 36. Recommended `.gitignore`

Use an appropriate `.gitignore`.

Typical Python entries:

``` gitignore
__pycache__/
*.py[cod]
*.so

.venv/
venv/
env/

.env
.env.*

!.env.example

.pytest_cache/
.coverage
htmlcov/

*.db
*.sqlite
*.sqlite3

.DS_Store

.vscode/
.idea/

node_modules/
dist/
build/

*.log
```

If the project intentionally needs a database file or other generated
artifact, explicitly decide that with the team instead of blindly
ignoring it.

------------------------------------------------------------------------

# 37. Recommended CODEOWNERS

If GitHub is being used, create:

``` text
.github/CODEOWNERS
```

Example:

``` text
/services/rag/        @rag-owner
/services/llm/        @ai-owner
/models/              @backend-owner
/routes/              @backend-owner
/templates/           @frontend-owner
/static/              @frontend-owner
/docs/                @docs-owner
```

This makes it clear who should review sensitive areas.

------------------------------------------------------------------------

# 38. Team Communication Tags

Use these tags in your team chat:

``` text
[WORKING]
[READY]
[BLOCKED]
[CONFLICT]
[API CHANGE]
[DB CHANGE]
[RAG CHANGE]
[BREAKING CHANGE]
[INTEGRATION]
[URGENT]
```

Example:

``` text
[RAG CHANGE]

I changed the Chroma Cloud retrieval pipeline.

Files:
services/rag/

Impact:
All AI/RAG features.

Please do not merge other RAG changes until this PR is reviewed.
```

------------------------------------------------------------------------

# 39. If Two People Need the Same File

Use this protocol:

``` text
Person A:
"I am editing app.py lines/routes X."

Person B:
"I also need app.py."

Decision:
A finishes route X first.
B works on service Y separately.
B adds the route after A merges.
```

Do NOT both rewrite the same section simultaneously.

------------------------------------------------------------------------

# 40. If Someone Has Uncommitted Work

Before pulling or switching branches, protect it:

``` bash
git status
git add .
git commit -m "wip: save local progress"
```

or:

``` bash
git stash
```

Do not delete another person's local changes.

------------------------------------------------------------------------

# 41. Safe Recovery

If you accidentally break your branch:

``` bash
git status
git log --oneline --max-count=10
```

Do not immediately run destructive commands.

Avoid:

``` bash
git reset --hard
git clean -fd
git push --force
```

unless you fully understand the consequences.

For shared branches, NEVER force-push without explicit team agreement.

------------------------------------------------------------------------

# 42. Golden Integration Principle

The team should optimize for:

``` text
SMALL DIFF
+
CLEAR OWNERSHIP
+
STABLE INTERFACE
+
FREQUENT INTEGRATION
+
AUTOMATED TESTS
=
LOW MERGE CONFLICT
```

Not:

``` text
everyone works independently for 12 hours
+
everyone merges at the end
=
DISASTER
```

------------------------------------------------------------------------

# 43. AbhyasAI-Specific Ownership Recommendation

A practical split for this project:

``` text
TEAM 1 — RAG / AI
services/rag/
services/llm/
Chroma Cloud
citations
retrieval
prompting

TEAM 2 — STUDENT INTELLIGENCE
mastery
adaptive quiz
study planner
"What Should I Study Now?"
panic mode

TEAM 3 — EXAM INTELLIGENCE
PYQ analysis
blueprints
exam simulator
answer evaluation
historical relevance

TEAM 4 — VIVA
viva engine
personas
evaluation
viva UI

TEAM 5 — FRONTEND
dashboard
quiz UI
viva UI
study planner UI
source viewer

TEAM 6 — BACKEND / DATA
routes
models
database
authentication
shared APIs

TEAM 7 — INTEGRATION / QA
end-to-end testing
demo flow
bug fixing
performance
deployment
documentation
```

Adjust this according to the actual number of teammates.

------------------------------------------------------------------------

# 44. The One-Line Rule Everyone Must Remember

> **If your change can be made without touching someone else's area, do
> it that way.**

And:

> **If you must touch their area, communicate before doing it.**

------------------------------------------------------------------------

# 45. Final Hackathon Integration Command Sequence

For the integration manager:

``` bash
git switch main
git pull origin main

git switch integration
git pull origin integration

git merge <feature-branch-1>
git merge <feature-branch-2>
git merge <feature-branch-3>

python -m compileall .
pytest

git grep -n "<<<<<<<\|=======\|>>>>>>>"

git push origin integration
```

Then manually verify the complete AbhyasAI journey:

``` text
Login
 ↓
Upload syllabus
 ↓
Upload PYQs
 ↓
Ingestion
 ↓
Chroma Cloud
 ↓
Ask AI
 ↓
Retrieved evidence
 ↓
Gemini answer
 ↓
Citations
 ↓
Mastery
 ↓
What should I study?
 ↓
Adaptive quiz
 ↓
Answer evaluation
 ↓
Viva
 ↓
Exam simulation
 ↓
Dashboard
```

Only after this end-to-end flow is stable should `integration` be merged
into `main`.

------------------------------------------------------------------------

# 46. Final Team Agreement

Every teammate agrees to:

``` text
[ ] I will use my own feature branch.
[ ] I will not push directly to main.
[ ] I will pull before starting work.
[ ] I will keep commits small.
[ ] I will not commit secrets.
[ ] I will avoid unnecessary shared-file changes.
[ ] I will communicate API/database/RAG breaking changes.
[ ] I will run tests before requesting a merge.
[ ] I will resolve conflicts carefully.
[ ] I will not overwrite another person's work.
[ ] I will integrate frequently.
[ ] I will prioritize stability near the deadline.
```

## THE TEAM'S CORE RULE

> **Build independently. Integrate continuously. Communicate before
> touching shared infrastructure. Test before merging.**

This is the team's source of truth for Git collaboration during the
hackathon.
