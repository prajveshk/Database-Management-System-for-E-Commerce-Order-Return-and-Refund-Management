# PPT3 Presentation Script — Final Demonstration (Review 3)

**Project:** Design and Implementation of a Database Management System
for E-Commerce Order, Return and Refund Management
**Speaker:** Kakaraparthi Komal Prajvesh (25WU0102114)
**Duration:** ~9 minutes + Q&A | **Lanugage:** English, steady pace (~130 words/min)

> CUES IN CAPS are stage directions, not spoken words.

---

## Slide 1 — Title (30 sec)

**On screen:** Title, name, roll number, tagline.

**Say:**

> "Good morning, faculty. I am Kakaraparthi Komal Prajvesh, roll number
> 25WU0102114. In Reviews 1 and 2 I presented the design and the
> implementation of my DBMS project. Today, in Review 3, I will demonstrate
> the complete working system, its validation results, and the conclusion.
> The project delivers controlled lifecycle management from order placement
> to refund and audit — one lifecycle, one source of truth."

**[NEXT SLIDE]**

---

## Slide 2 — Project Arc (60 sec)

**On screen:** Review 1 → 2 → 3 journey; 4 outcomes; system inventory.

**Say:**

> "The project moved in three stages. Review 1 fixed the requirements: the
> problem statement, SRS, three-layer architecture, and the first schema.
> Review 2 converted that design into a normalized schema with SQL triggers,
> a refund procedure, APIs, and first-round tests. Review 3, today, is the
> complete validated system. Four outcomes define it: a single source of truth
> for order, return, and refund; enforced state transitions; a full audit
> trail; and role-based access. The final inventory is 13 tables in Third
> Normal Form, 5 triggers, 1 stored procedure, 17 REST endpoints retained as
> the automated test harness, and 6 Streamlit application pages that form the
> user-facing system."

**[NEXT SLIDE]**

---

## Slide 3 — System Design (75 sec)

**On screen:** Client / Service / Data layers; lifecycle-to-entity table.

**Say:**

> "The architecture has three layers. The client layer is a Streamlit
> application with a customer portal and an operations dashboard. The service
> layer covers authentication, ordering, returns, refunds, and notification
> hooks. The data layer is a MySQL 8 InnoDB database with constraints,
> transactions, indexes, an audit log, and verified backups. The table below
> shows how the lifecycle maps to entities: a customer places an order, an
> order carries items, items become return items, inspection verdicts decide
> refunds, and the audit log records everything. Since Review 1, four things
> were added from examiner feedback: item-level returns for partial refunds,
> a dedicated Inspection table, the AuditLog, and role tables. All 13 tables
> are in 3NF — reusable product data stays in Product, while each purchase
> freezes its historical price in OrderItem."

**[NEXT SLIDE]**

---

## Slide 4 — Implementation (75 sec)

**On screen:** 5 numbered behaviors; transaction path code block.

**Say:**

> "Implementation turns business rules into enforceable database behavior,
> not just application code. One — integrity: primary and foreign keys with
> ON DELETE RESTRICT, CHECK, UNIQUE, and ENUM domains, plus ten B-tree
> indexes. Two — traceability: triggers write every status change to the
> audit log automatically. Three — eligibility: a trigger blocks any return
> filed after the product's return window. Four — centralized logic: a single
> procedure, sp_process_refund, owns refund calculation, duplicate
> prevention, inventory restocking, and auditing. Five — recovery: the whole
> refund runs in one ACID transaction. The transaction path on screen is
> literal: BEGIN, call the procedure, restock GOOD-condition inventory,
> insert the audit row, COMMIT — and on any error the exit handler rolls back
> everything, so a failed refund can never leave half-written data."

**[NEXT SLIDE]**

---

## Slide 5 — LIVE DEMONSTRATION (3 min — the core of Review 3)

**On screen:** 7 demo steps + blocked-action note.

**Say:**

> "I will now demonstrate the live system. I am logged in as admin, which
> holds every operational right, so one session can walk the full lifecycle."

**[OPEN browser at http://127.0.0.1:8501 — Lifecycle Demo page]**

> "Step one — the customer places an order for wireless headphones; payment
> gets a mock gateway reference. Step two — the customer requests a return
> with a reason; the request opens in Requested state. Step three — support
> approves it. Note that approving a request that is not in Requested state
> would be rejected by the state-machine trigger. Step four — the warehouse
> marks it received. Step five — the warehouse inspects it as GOOD with a
> note. Step six — support processes the refund through the stored procedure:
> the amount is computed from the frozen purchase price, exactly once.
> Step seven — GOOD-condition stock is restocked to AVAILABLE, and the audit
> log gains a full trail with actor names and timestamps."

**[CLICK “Run full lifecycle demo”; READ OUT the success banner]**

> "Now the negative test — the blocked action. Order 3 is 45 days old but
> its product allows only a 7-day window."

**[GO TO Customer Portal → expander → “Test blocked late return”]**

> "The database itself rejects the request with ‘Return window expired’ —
> the application only displays the trigger's message. That is the design
> philosophy: rules live in the database, so no client can bypass them."

**[NEXT SLIDE]**

---

## Slide 6 — Security and Control (60 sec)

**On screen:** Permissions-by-role table; security controls; 403 note.

**Say:**

> "Each actor sees only what their job needs. Customers view orders and
> request returns. Support approves returns and processes refunds. Warehouse
> receives and inspects. Admin has full rights including the audit log and
> role management. Five controls back this up: parameterized queries against
> injection, input validation, bcrypt password hashing, no card data stored —
> only gateway references — and an admin-only audit log. A non-admin hitting
> the audit endpoint gets HTTP 403, which I have captured as evidence in the
> report."

**[NEXT SLIDE]**

---

## Slide 7 — Validation (75 sec)

**On screen:** 5-category test matrix; FIX 01/02/03.

**Say:**

> "Testing confirms correctness across rules, services, failures, and
> concurrency: 13 of 13 tests pass. Five constraint tests prove the engine
> rejects zero quantities, negative amounts, duplicate payment references,
> illegal status values, and restricted deletes. The unit test proves the
> refund procedure refuses any return not in Inspected state. Integration
> proves the API chain runs order to refund end to end. The rollback test
> forces a mid-procedure failure and confirms zero orphan rows — that was Fix
> 03. The concurrency test fires two simultaneous refunds and exactly one
> succeeds — Fix 02, duplicate prevention. Fix 01 was the state-transition
> trigger. Four additional Streamlit data-layer tests prove login and RBAC,
> the full lifecycle through the new UI layer, and both guards firing
> identically outside the API."

**[NEXT SLIDE]**

---

## Slide 8 — Performance (60 sec)

**On screen:** 1K/10K/100K table; procedure time; backup/restore verdict.

**Say:**

> "Indexing keeps response stable as data grows. Pending-returns lookups run
> in 0.22 milliseconds at 1,000 records and under 3 milliseconds at 100,000.
> The refund procedure medians 1.23 milliseconds. EXPLAIN confirms indexed
> plans use ref access on the status index while unindexed plans fall back to
> full scans. For disaster recovery, a mysqldump backup of 111,025 orders was
> restored with a matching checksum — full recovery verified, not assumed."

**[NEXT SLIDE]**

---

## Slide 9 — Impact (60 sec)

**On screen:** Before/after table; limitations.

**Say:**

> "Against the old spreadsheet process: status visibility moves from manual
> logs to one lifecycle record; audit goes from absent to traceable; invalid
> transitions from possible to blocked; refunds from duplication-prone to a
> centralized exact-once procedure. I state the limitations honestly: demo
> and bulk-simulated data, a mocked payment gateway with no bank network, no
> production-scale or multi-region testing, and a single database instance.
> Each maps to future work on the final slide."

**[NEXT SLIDE]**

---

## Slide 10 — Conclusion (45 sec)

**On screen:** Conclusion + future scope + Thank You / Q&A.

**Say:**

> "All objectives were met: a normalized schema, ACID transactions for safe
> state changes, a state machine for a controlled lifecycle, and indexing
> for responsive growth. Future scope is an analytics dashboard extension,
> ML-based fraud and return-risk prediction, automated eligibility, event
> notifications, and cloud replication. One lifecycle, one source of truth.
> Thank you — I welcome your questions."

---

## Appendix — Likely Q&A (prepare, do not present)

1. **Why put rules in triggers instead of the app?**
   Triggers execute for every writer — app, procedure, or manual SQL — so no
   client can bypass eligibility, quantity, or state rules.
2. **How is a duplicate refund impossible?**
   The procedure locks the return row, requires Inspected state, checks zero
   processed refunds exist, and the concurrency test proves exactly-once
   behavior under parallel attempts.
3. **Why keep FastAPI if the UI is Streamlit?**
   FastAPI is frozen as the automated test and benchmark harness; Streamlit
   is the user-facing application with direct parameterized connectivity.
4. **What breaks first at 10× scale?**
   Single-instance limits: no read replicas; the 100K benchmark and the
   RDS-migration future item address exactly this.
5. **Where is card data?**
   Nowhere — only mock provider references are stored, by design.
