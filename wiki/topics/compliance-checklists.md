---
title: Action checklist and youth participation reminder
program: SHARED
year: 2026
kind: method
---

# Checklist for action

The checklists are a map of controls with sources, not a prior certification. The file must contain project-specific outcomes and evidence. **KA152 has in-depth but partial coverage; the other six Youth actions have targeted controls; other routes have explicit routing only.** Don't claim that every detail of every action has been verified.

## Uso da parte dell’orchestratore

1. Set program, annuality, action, sector, role/management and round. Read `config/compliance/routing-coverage.json`: A `routing-only-not-assessed` route requires specific matrix construction before approving the relevant step.
2. Apply `shared.json` and the exact profile of the action, filtering `stages`: `ALL` means each phase. Do not apply the KA152 checklist to any KA1 or the KA220 Youth template to any other sector.
3. Open the entire action section and the general conditions, relevant standards, correct expert guidance, national source and current form. Check IDs are stable; extend with new evidence, without erasing the gaps.
4. For each control produce: `check_id`, `status`, `evidence`, `artifact_locators`, `discrepancy`, `severity`, `required_fix`, `owner`. States: `satisfied / not-satisfied / to-verify / not-applicable`; NA requires motivation and scope. A good intention does not prove a consultation that has already taken place.
5. At the end of the phase an independent validator, with new context, reads the frozen package, phase contract and checklist. Report defects with evidence and coverage gaps; does not receive the desired outcome. The gate scheme and mechanism are the responsibility of the coordinator, not a property that these checklists alone guarantee.

`classification=requirement` indicates a source condition; `award-criterion` an element evaluated qualitatively; `recommendation` a recommendation; `good-practice` an operational or internal policy translation. The severity depends on the nature and effect of the defect. A recommendation does not automatically become a reason for inadmissibility. The shared baseline is the assistant's policy, distinct from the tender rules.

## KA152 Reminder: Young people contribute before applying

For Youth Exchanges young people must have real opportunities to play an active role in planning, preparation, implementation and follow-up. The program guide describes this element with qualitative wording `should`, and the design grid evaluates involvement in all phases: **not a new numerical eligibility threshold**. The assistant remembers this as a necessary quality control at each relevant step. [Official guide: Setting up a project and Learning process](https://erasmus-plus.ec.europa.eu/programme-guide/part-b/key-action-1/youth-exchanges).

| Phase | Critical question | Try to ask |
|---|---|---|
| Before the question | What needs, goals, methods or choices have been defined/changed by young people? | Real consultations, contributions and decisions; state what is missing. |
| Preparation | What tasks and decisions are actually open to young people, with accessible support? | Responsibility matrix and preparation plan. |
| Implementation | How do they implement the program together and can they adapt it? | Timetable, non-formal methods, tasks and role of guardianship of adults. |
| Follow-up | How do they reflect, evaluate, document and use/share learning? | Feedback plan, Youthpass, responsibilities and subsequent checks. |

Recommended register: phase, group involved, open decision, contribution, effective influence, support for barriers, evidence. A youth-led statement without this data is weak. The safety responsibility of adults should not be transferred to minors. Don't invent consultations retroactively. Primary local source: `programme-2026:p0154–p0155`, grid p0160; expert guide `expert-2026:p0022–p0023`.

## Specific controls and local sources

The pages shown are **physical pages of the PDF**. In JSON each reference contains source ID, locator, immutable revision path and hash. The controls primarily summarize user-provided PDFs; live checks corroborate specific sections. Deadlines, rates and round availability must be confirmed for the concrete application.

### KA150 — targeted-partial

| ID | Class | Control | Source |
|---|---|---|---|
| `ka150-experience` | requirement | Organization legally established at least two years before the deadline and at least two years of relevant youth experience; operational/financial capacity and standards to be verified. | programme-2026 p.145; programme-2026 p.146 |
| `ka150-plan` | award-criterion | Accreditation evaluates long-term plan and management integrated into ordinary activity; do not automatically apply form/address book KA152. | programme-2026 p.146; programme-2026 p.147 |

### KA151 — targeted-partial

| ID | Class | Control | Source |
|---|---|---|---|
| `ka151-accreditation` | requirement | Access reserved for accredited youth organizations; only one question per call/year. Check the validity and status of the accreditation. | programme-2026 p.149; programme-2026 p.150 |
| `ka151-activity-specific` | requirement | For Youth Exchanges/PDA apply descriptive and eligibility criteria of the respective activity; outreach only with PDA; do not transfer the standard application rules without checking accredited variant. | programme-2026 p.150 |
| `ka151-allocation` | requirement | Accredited request uses allocation rules published by the agency; do not invent new competitive 30/40/30 grids or rates from old workbooks. | programme-2026 p.150; programme-2026 p.151 |

### KA152 — detailed-partial

#### Partecipazione e apprendimento

| ID | Class | Control | Source |
|---|---|---|---|
| `ka152-youth-planning` | award-criterion | Before applying, young people help identify needs, objectives, learning outcomes, program and methods. A project written entirely by adults with only subsequent participation does not demonstrate this element. | programme-2026 p.154; programme-2026 p.155; programme-2026 p.160; expert-2026 p.22 |
| `ka152-youth-preparation` | award-criterion | Envisage concrete roles for young people in practical, intercultural, linguistic and task preparation, proportionate to age, ability and supports. | programme-2026 p.154; programme-2026 p.155; programme-2026 p.160; expert-2026 p.22 |
| `ka152-youth-implementation` | award-criterion | Youth groups implement a non-formal learning program together: demonstrating co-leadership, division of tasks and possibilities for adaptation, with safe adult support. | programme-2026 p.154; programme-2026 p.155; programme-2026 p.160; expert-2026 p.22 |
| `ka152-youth-follow-up` | award-criterion | Young people participate in evaluation, reflection and documentation of learning, dissemination and use of results. | programme-2026 p.154; programme-2026 p.155; programme-2026 p.160; expert-2026 p.22 |
| `ka152-participation-proof` | good practice | Distinguish consultation, decision and management: document which choices young people can change, who is excluded and how feedback is given. It's not enough to write youth-led. | programme-2026 p.154; programme-2026 p.155 |
| `ka152-non-formal` | requirement | Exclude tourism, holidays, festivals, performance tours, statutory meetings, academic trips and courses run by adults for young people; verify a non-formal program created together by the groups. | programme-2026 p.153 |

#### Partnership and composition of activities

| ID | Class | Control | Source |
|---|---|---|---|
| `ka152-partners` | requirement | Identify all organizations applying; minimum two from different countries, at least one sending and one receiving; check legal categories and countries allowed. | programme-2026 p.154; programme-2026 p.156; programme-2026 p.157; programme-2026 p.158 |
| `ka152-oid-cap` | requirement | The same OID cannot appear in more than five applications per deadline in this action, as an applicant or partner. | programme-2026 p.157 |
| `ka152-duration` | requirement | Project 3–24 months; each exchange 5–21 days excluding travel. Distinguish project and activity duration. | programme-2026 p.157 |
| `ka152-participants` | requirement | Young people 13–30 years old at the start date, resident in the countries of the sending/receiving organizations; distinguish adult leaders/facilitators/companions from participants. | programme-2026 p.158 |
| `ka152-group-size` | requirement | 16–60 participants per activity, at least four per group and at least two groups from different countries; minimum ten only if all young people have fewer opportunities. Leaders, facilitators and companions excluded from the count. | programme-2026 p.158 |
| `ka152-leaders` | requirement | At least one group leader per group; maximum two facilitators per activity; leaders, facilitators and companions at least eighteen years old. | programme-2026 p.158 |
| `ka152-venue` | requirement | Headquarters in the country of one or more participating organizations for itinerant activities; no activity in Belarus or Russia. At least one sending/receiving organization of the activity must be from the country of the receiving agency. | programme-2026 p.158 |
| `ka152-neighbour-countries` | requirement | If non-associated neighboring countries are involved, check regions 1–4 and at least one organization from an EU/associated country plus one from a non-associated neighboring country; do not use all countries of the world indiscriminately. | programme-2026 p.158 |

#### Attachments, media and protection

| ID | Class | Control | Source |
|---|---|---|---|
| `ka152-timetable-annex` | requirement | Attach timetable of each Youth Exchange and planned preparatory visit; check in the current form format and upload. This attachment is required by the guide. | programme-2026 p.157 |
| `ka152-accession` | requirement | Check the organizations' accession forms: to be provided upon application and at the latest upon signature of the grant agreement, according to the note and general conditions; do not confuse with internal partner agreement. | programme-2026 p.156 |
| `ka152-preparatory` | requirement | If required, preparatory visit: in the country of a receiving party before the exchange; purpose quality, partnership and participant needs; people also expected in the main activity. | programme-2026 p.153; programme-2026 p.159 |
| `ka152-fees` | requirement | If contributions to participants: very low, proportionate, motivated by direct benefit, explained, non-profit, without barriers and declared in the report. Participants with fewer opportunities and additional fees from the chosen suppliers are prohibited. | programme-2026 p.154 |
| `ka152-standards` | requirement | Apply Erasmus Youth Quality Standards for selection, preparation, learning, recognition and sharing; read the full document, not this checklist alone. | programme-2026 p.155 |
| `ka152-safety` | award-criterion | Effective protection measures, safe respectful non-discriminatory environment and risk management before departure; explicit group leaders' support roles. | programme-2026 p.155; programme-2026 p.160 |

#### Needs, learning, priorities and quality

| ID | Class | Control | Source |
|---|---|---|---|
| `ka152-needs` | award-criterion | Documented needs of young people and organizations, consistent learning methods and outcomes; distinguish real local data from generic European needs. | programme-2026 p.154; programme-2026 p.159; expert-2026 p.22 |
| `ka152-recognition` | award-criterion | Reflection, identification and documentation of learning, with support from organizations and appropriate use of Youthpass; do not reduce Youthpass to the final certificate. | programme-2026 p.155; programme-2026 p.160; expert-2026 p.23 |
| `ka152-inclusion` | award-criterion | Accessible and inclusive activities; involve young people with fewer opportunities in decisions; verify concrete barriers and supports, diversity and balance between countries and genders. | programme-2026 p.155; programme-2026 p.160; expert-2026 p.22 |
| `ka152-priorities` | award-criterion | Link the project to action objectives and one or more priorities of the EU Youth Dialogue or Youth Goals; make inclusive, green, digital and participatory dimensions coherent without inventing contributions. | programme-2026 p.152; programme-2026 p.159 |
| `ka152-green-digital` | award-criterion | Sustainable practices and appropriate methods, including any digital elements; motivate digital with respect to learning/accessibility, without imposing useless online activities. | programme-2026 p.156; programme-2026 p.160 |
| `ka152-management` | award-criterion | Responsibility, cooperation and communication, practical support, evaluation of phases, internal/external dissemination and sustainability of concrete results. | programme-2026 p.160 |
| `ka152-rubric` | award-criterion | Use grid 30 relevance/rationale/impact, 40 design, 30 management: at least 60/100 and half of each category; Thresholds are not a promise of financing. | programme-2026 p.159; programme-2026 p.160 |

### KA153 — targeted-partial

| ID | Class | Control | Source |
|---|---|---|---|
| `ka153-pda` | requirement | Include at least one Professional Development Activity; system development/outreach is complementary, it does not replace professional mobility. | programme-2026 p.167 |
| `ka153-workers-role` | award-criterion | Youth workers and organizations have an active role in the four phases; base selection and design on real professional needs and demonstrate transfer into routine practice with young people. | programme-2026 p.168 |
| `ka153-transfer` | award-criterion | Results/methods/tools recognized, transferable and used in organizations: predict adoption, accountability and follow-up beyond publication. | programme-2026 p.168 |
| `ka153-outreach` | good practice | Distinguish system development/outreach from ordinary follow-up dissemination; motivate value for the youth work system and consistency with PDA. | programme-2026 p.166; programme-2026 p.167 |
| `ka153-annex` | requirement | Timetable of each PDA, preparatory visit and planned system development/outreach activity; check duration and counts in the full section. | programme-2026 p.171 |

### KA154 — targeted-partial

| ID | Class | Control | Source |
|---|---|---|---|
| `ka154-meaningful` | award-criterion | Meaningful participation of young people at all stages, with adaptable intensity but aligned with the principles; do not transform meetings organized by adults into only nominal participation. | programme-2026 p.183; programme-2026 p.184 |
| `ka154-feedback` | recommendation | Follow-up with return to young people of the concrete results and how communicated/used by the stakeholders. | programme-2026 p.184 |
| `ka154-all-learning` | requirement | Support reflection and documentation of the learning of all participants, even beyond the group preparing/implementing the project, in particular Youthpass. | programme-2026 p.184 |
| `ka154-events` | requirement | Event financing: physically present audience larger than just the implementing group; participation in a third-party event does not generate event-specific funding; distinguish event with/without mobility. | programme-2026 p.182; programme-2026 p.183 |
| `ka154-excluded` | requirement | Exclude statutory meetings, partisan political events and permanent physical infrastructure; mobility must support other project activities. | programme-2026 p.182; programme-2026 p.183 |
| `ka154-eu-dimension` | award-criterion | Even a national project must have a European dimension and connection with EU values/themes, civic participation and opportunities to influence decisions. | programme-2026 p.182 |

### KA155 — targeted-partial

| ID | Class | Control | Source |
|---|---|---|---|
| `ka155-target` | requirement | DiscoverEU inclusion concerns young people with fewer opportunities 18–21, not the general DiscoverEU call for 18-year-olds; verify legal residence and age at the applicable time. | programme-2026 p.201 |
| `ka155-co-design` | award-criterion | Young people with fewer opportunities participate in all phases; contribute to needs, learning, itinerary, activities and preparation, with proportionate support. | programme-2026 p.197; programme-2026 p.198 |
| `ka155-travel` | requirement | An organization; trips 1–30 days with 1–5 participants and companions if necessary; at least one other country than the country of departure. | programme-2026 p.200; programme-2026 p.201 |
| `ka155-fees` | requirement | Do not collect contributions from young people with fewer opportunities or additional fees from chosen suppliers. | programme-2026 p.197 |
| `ka155-support` | award-criterion | Protection and support before/during travel, learning documented with Youthpass and sustainable travel practices. | programme-2026 p.198; programme-2026 p.199 |
| `ka155-round` | requirement | Additional round on October 1st is optional and must be opened by the agency: do not hire available in Italy without current AIG source. | programme-2026 p.200 |

### KA220-YOU — targeted-partial

| ID | Class | Control | Source |
|---|---|---|---|
| `ka220-you-youth-context` | award-criterion | Profile, experience and activities of organizations relevant to the youth sector; genuine needs of targets and organisations, complementarity and proven European value. | programme-2026 p.240 |
| `ka220-you-partners-role` | award-criterion | All partners have active contributions and tasks consistent with expertise; comprehensive preparation, implementation and follow-up plan with people involved. | programme-2026 p.239; programme-2026 p.241 |
| `ka220-you-youth-participation` | award-criterion | Civic participation and inclusive decision-making opportunities appropriate to the target; do not transfer by analogy the formal composition/groups/age requirement KA152 to KA220. | programme-2026 p.239; programme-2026 p.240; programme-2026 p.241 |
| `ka220-you-wp-management` | requirement | Dedicated WP management and maximum 20% of the total; objectives/results for implementation WP. Maximum four WP implementation is recommendation, not outright ban. | programme-2026 p.243 |
| `ka220-you-wp-count` | recommendation | If over four WP implementation, justify necessity and readability; the WP2–6 user template does not impose five WPs. | programme-2026 p.243 |
| `ka220-you-impact` | award-criterion | Realistic qualitative/quantitative indicators; verifiable routine adoption, impact on targets/communities, external use, dissemination, open licensing when relevant and sustainability. | programme-2026 p.241; programme-2026 p.242 |
| `ka220-you-finance` | requirement | Lump sums 120k/250k/400k proportionate to assets; estimated overall cost higher than the amount requested for co-financing. Do not use rates workbook as the official rate. | programme-2026 p.242; programme-2026 p.243 |

## Confini da rispettare

- KA153 concerns professional learning of youth workers and transfer into their practice: the active role is about them, not a copied requirement of young people 13–30. [Official section KA153](https://erasmus-plus.ec.europa.eu/programme-guide/part-b/key-action-1/mobility-youth-workers).
- KA154 requires significant participation; provides for the return of results to young people and learning also for participants beyond the implementing group. A funded event has its own conditions and is not participation in a third party event. [Official section KA154](https://erasmus-plus.ec.europa.eu/programme-guide/part-b/key-action-1/youth-participation).
- KA155 is DiscoverEU inclusion for young people with fewer opportunities 18–21: co-planning of the trip and specific supports. The October round is optional, to be confirmed with AIG. [Official section KA155](https://erasmus-plus.ec.europa.eu/programme-guide/part-b/key-action-1/discovereu).
- KA150 is accreditation, KA151 request for accredited organizations and allocation: KA152 are not application standards. [Official section KA150](https://erasmus-plus.ec.europa.eu/programme-guide/part-b/key-action-1/erasmus-accreditation-youth). Attempting to open live URL KA151 in routing did not return section: local source verified p149–151, Subsequent check opened [the correct KA151 section](https://erasmus-plus.ec.europa.eu/programme-guide/part-b/key-action-1/mobility-accredited-youth). The 2021 exception still reported on the page is not a 2026 rule.
- KA220-YOU uses Youth criteria and form and its own cooperation logic. Does not inherit KA152 number/groups/age; four WP implementation are recommended, maximum management 20% is a limit. [Official section Cooperation Partnerships](https://erasmus-plus.ec.europa.eu/programme-guide/part-b/key-action-2/cooperation-partnerships).
- ESC maintains its own sources and criteria. The seven ESC routes are in the coverage registry, but this extension does not build or approve the relevant regulatory checklists.

## KA1 without question-by-question guidance

KA1 forms can also be acquired without a suggestion table. For each question the planner connects verified requirements and criteria, necessary data, structure and effective limit of the field. It must distinguish the assistant's editorial mapping from the official instruction of the form. Without a real form he can build the design and checklist of the action, but cannot invent questions, characters or mandatory fields.

## Maintenance and memory

Reusable profiles remain in `config/compliance/`; a copy with specific outcomes lives in your application file. Do not update the reusable baseline with single project assumptions. Help or call update requires review for scope, hash/version, and differences; Phase approval does not authorize the application or predict funding. Store checklists, evidence, decisions and control results, not internal reasoning.
