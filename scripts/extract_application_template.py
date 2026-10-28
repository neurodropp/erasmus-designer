#!/usr/bin/env python3
"""Extract the supplied editorial KA220 template without treating it as a call.

Requires the bundled python-docx runtime. Outputs are deterministic for identical
DOCX input. The curated mapping applies to this specific template, not arbitrary
application forms; structural changes require another review.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import posixpath
import re
import shutil
from pathlib import Path
from zipfile import ZipFile

from docx import Document
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ID = "template-ka220-user"
ORIGINAL_NAME = "KA220 E+ Project Template (2).docx"
SUPPORTED_TEMPLATE_SHA256 = "98cf086373f9b076858491367b1639b5c14a1cf292fa6dd43e4d946aa7334ecf"
LIMIT_RE = re.compile(r"\((\d+)\s+chars(?:\s+description)?\)", re.I)
GROUPS = {
    "R": ("Relevance", 25, 13),
    "D": ("Quality of the project design and implementation", 30, 15),
    "P": ("Quality of the partnership and the cooperation arrangements", 20, 10),
    "I": ("Impact", 25, 13),
}

# Official subcriterion statements are stored separately from our editorial
# question-to-criterion associations. Pages are PDF file pages, also printed
# with the same number in the supplied guides.
CRITERIA_ROWS = [
    ("R.priority", 240, [45], "the proposal is relevant for objectives and priorities of the Action", "Relevance to applicable objectives and priorities"),
    ("R.values", 240, [46], "the proposal is relevant for the respect and promotion of shared EU values", "EU values and non-discrimination embedded in the project"),
    ("R.profile", 240, [46], "the profile, experience and activities of the participating organisations are relevant for the field of the application", "Relevant organisational profile, activities and experience"),
    ("R.needs", 240, [46, 47], "the proposal is based on a genuine and adequate needs analysis", "Genuine and adequate needs analysis"),
    ("R.synergy", 240, [47], "the proposal is suitable for creating synergies between different fields of education, training, youth and sport or it has potentially a strong impact on one or more of those fields", "Cross-sector synergies or strong potential impact in one or more fields"),
    ("R.innovation", 240, [47], "the proposal is innovative", "Innovation in the relevant field or context"),
    ("R.complementarity", 240, [47], "the proposal is complementary to other initiatives already carried out by the participating organisations", "Complementarity and added value in relation to existing initiatives"),
    ("R.eu", 240, [47], "the proposal brings added value at EU level through results that would not be attained by activities carried out in a single country", "European added value needed to achieve the results"),
    ("D.objectives", 241, [48], "the project objectives are clearly defined, realistic and address needs and goals of the participating organisations and the needs of their target groups", "Clear, realistic objectives linked to identified needs"),
    ("D.method", 241, [48], "the proposed methodology is clear, adequate and feasible", "Clear, appropriate and feasible methodology"),
    ("D.plan", 241, [48], "the project work plan is clear, complete and effective, including appropriate phases for preparation, implementation and sharing project results", "Complete work plan with coherent phases"),
    ("D.cost", 241, [49], "the project is cost-effective and allocates appropriate resources to each activity", "Cost-effectiveness and appropriate resources for each activity"),
    ("D.qa", 241, [49], "the project proposes appropriate quality control, monitoring and evaluation measures to ensure that the project implementation is of high quality, completed in time and on budget", "Quality control, monitoring and evaluation with timely corrective action"),
    ("D.inclusion", 241, [49], "the activities are designed in an accessible and inclusive way and are open to people with fewer opportunities", "Accessible and inclusive activities"),
    ("D.digital", 241, [50], "the project incorporates the use of digital tools and learning methods to complement their physical activities, and to improve the cooperation between partner organisations", "Digital tools and learning integrated with activities and cooperation"),
    ("D.green", 241, [50], "The project is designed in an eco-friendly way and incorporates green practices in different project phases", "Environmental practices across project phases"),
    ("D.participation", 241, [50], "The project encourages participation and civic engagement", "Active participation and civic engagement"),
    ("D.indicators", 241, [50], "The project clearly describes both qualitative and quantitative indicators, that are realistic, feasible, and contribute to strengthening the overall quality of the project", "Realistic and useful qualitative and quantitative indicators"),
    ("D.learningfit", 241, [51], "the extent to which these activities are appropriate for the project's objectives and involve the appropriate profile and number of participants", "Where learning activities are planned: appropriate participant profiles and numbers"),
    ("D.learningpractical", 241, [51], "the quality of practical arrangements, management and support modalities in learning, teaching and training activities", "Where learning activities are planned: high-quality arrangements and practical support"),
    ("D.recognition", 241, [52], "the quality of arrangements for the recognition and validation of participants' learning outcomes, in line with European transparency and recognition tools and principles", "Where learning outcomes are planned: recognition aligned with the sector"),
    ("P.mix", 241, [53, 54], "the project involves an appropriate mix of participating organisations in terms of profile, including grassroots organisations, past experience in the Programme and expertise to successfully complete all project objectives", "Appropriate partner mix, capacity and complementarity"),
    ("P.newcomers", 241, [54], "the project involves newcomers and less experienced organisations to the Action", "Meaningful involvement of newcomers and less experienced organisations"),
    ("P.tasks", 241, [53, 54], "the proposed allocation of tasks demonstrates the commitment and active contribution of all participating organisations", "Roles and tasks demonstrate active contribution"),
    ("P.coordination", 242, [54], "the proposal includes effective mechanisms for coordination and communication between the participating organisations, as well as with other relevant stakeholders", "Effective coordination and communication"),
    ("P.third", 242, [54], "If applicable, the extent to which the involvement of a participating organisation from a third country not associated to the Programme brings an essential added value to the project", "Where relevant: essential added value of the non-associated partner"),
    ("I.integration", 242, [54], "the project proposal includes concrete and logical steps to integrate the project results in the regular work of participating organisations", "Integration of results into the organisations' regular work"),
    ("I.direct", 242, [55], "the project has the potential to positively impact its participants and participating organisations, as well as their wider communities", "Positive impact on participants, organisations and communities"),
    ("I.wider", 242, [55], "the expected project results have the potential to be used outside the organisations participating in the project during and after the project lifetime, and at local, regional, national or European level", "Use of results beyond the partnership and project lifetime"),
    ("I.dissemination", 242, [56], "the project proposal includes concrete and effective steps to make the results of the project known within the participating organisations, to share the results with other organisations and the public, and to publicly acknowledge the European Union funding", "Targeted dissemination, use and acknowledgement of EU funding"),
    ("I.open", 242, [56], "if relevant, the extent to which the proposal describes how the materials, documents and media produced will be made freely available and promoted through open licences, and does not contain disproportionate limitations", "Where relevant: open access and licences without disproportionate restrictions"),
    ("I.sustain", 242, [57], "the project proposal includes concrete and effective steps to ensure the sustainability of the project, its capacity to continue having an impact and producing results after the EU grant has been used up", "Sustainability and continuity after the EU grant"),
]


def spec(identifier, title, codes, components, critique, note=""):
    return {"id": identifier, "title": title, "codes": codes.split(),
            "components": components.split(" | "), "critique": critique,
            "curation_note": note}


SPECS = {
    6: spec("partner-profile", "Organisation profile", "R.profile P.mix", "Identity, legal form and mission | Relevant activities and usual target groups | Demonstrable experience in the topic | Capacity: staff, volunteers, learners and members | Specific contribution to the project", "Does the profile demonstrate capacity for the assigned role, or read like a brochure? Verify figures and consistency with the OID and tasks."),
    7: spec("partner-experience-staff", "Relevant experience and key people", "R.profile P.mix P.tasks", "Relevant experience and methods with documented results | Relevant cooperation and projects, if any | Key people: roles and functional skills | Complementarity between organisational and individual capacity | Capacity for the tasks and contribution to the consortium", "Does each cited skill serve a task? Verify identity, availability and qualifications; avoid decorative CVs.", "The phrase financial manager mandatory comes from the template; it does not prove that the 2026 form requires naming a specific profile."),
    8: spec("partner-past-participation", "Comments on previous participation", "R.profile P.mix P.newcomers", "Factual clarification of participation, if needed | Documented learning and improvements | Relevance to the current application | Strengthened management and reliability | Relevant information missing from other sections", "Does this section clarify facts and learning, or repeat the timeline? Do not invent experience for a newcomer.", "Optionality is a template recommendation and must be confirmed against the actual form. The box's reference to associated partners does not mean they must be placed here."),
    33: spec("selected-priorities", "Selection of the main and additional priorities", "R.priority", "Main priority relevant to the objectives and sector | Up to two additional priorities, only as allowed by the template field | Evidence of the link between priorities and the project", "Are the priorities valid for the actual year and sector? The template catalogue is not updated for 2026.", "T33 marks SCH, VET and ADU as not updated. The template does not include a complete Sport catalogue; do not transfer multiple selection to centrally managed Sport."),
    34: spec("priorities-addressed", "How the project addresses the priorities", "R.priority D.objectives", "Selected priority and relevant need | Objective that operationalises each priority | Corresponding activities, results and target groups | Evidence or indicator of contribution in the field", "Is there a verifiable mechanism for each priority? Copying the official wording is not enough."),
    35: spec("selected-topics", "Selection of topics", "R.priority R.needs", "Up to three topics available in the actual form | Direct link to needs and activities | Consistency with the selected sector and priorities", "Are these genuinely available and relevant selections? No choice shown in the screenshot is project data.", "The link to the criteria is indirect: topics do not receive a separate score."),
    36: spec("project-motivation", "Motivation and rationale for funding", "R.needs R.priority R.eu D.objectives", "Concrete problem and target groups in context | Gap in current solutions | Genuine, shared partner motivation | Relevance to applicable objectives and priorities | Expected change and need for funded cooperation", "Is the problem→gap→Erasmus+ response supported by evidence? Do not claim the idea predates the call unless documented."),
    37: spec("project-objectives-results", "Objectives, results and links to priorities", "D.objectives R.priority D.method", "Overall objective consistent with the problem | Realistic and observable specific objectives | Concrete results linked to each objective | Map of objectives→priorities→activities/WPs | Users and improvement of practices", "Are objectives, activities, outputs and outcomes distinguished? Justify numbers and targets; do not impose the template's 3–5 suggestion."),
    38: spec("project-innovation", "Innovation of the proposal", "R.innovation R.complementarity", "Defined innovation: content, method, process or organisation | Documented comparison with existing practices | Useful improvement for needs and users | Relevant organisational change | Conditions for adaptation and transferability", "What changes compared with which baseline? Avoid unverified superlatives and claims of being first; consider proportionality and target groups."),
    39: spec("project-complementarity", "Complementarity with existing initiatives", "R.complementarity R.innovation", "Relevant partner initiatives and available results | Gaps or unmet needs | Concrete added value of the new proposal | Integration of partners' experience | Continuity, reuse and pre-existing rights", "Does the new project add value or fund duplication? Verify cited projects and ownership of reused content."),
    40: spec("project-cross-sector-synergies", "Synergies and impact across fields", "R.synergy I.wider", "Fields directly involved and indirectly affected | Shared problem or strong impact in the main field | Transfer and interaction mechanisms | Credible changes in the stated fields | Value of the sectoral or cross-sector choice", "The question allows synergies OR strong impact in one or more fields: do not require a multi-sector approach. Describe uptake, not dissemination alone."),
    41: spec("project-european-added-value", "European added value", "R.eu I.wider", "Problem and differences across partners' contexts | Limits of national action alone | Necessary cooperation: comparison, co-creation and validation | Results usable and adaptable across contexts | Practical contribution to European objectives", "Which result depends on transnational cooperation? Travel or dissemination abroad is not enough."),
    42: spec("needs-to-address", "Needs to be addressed", "R.needs D.objectives", "Context, field, target groups and countries | Specific priority needs of groups and organisations | Available evidence, with sources and limitations | Common core and transnational differences | Implications and links to objectives", "Are the needs observable and evidenced, or are solutions disguised as needs? Do not assume the box's youth aged 17–24 or youth workers."),
    43: spec("target-groups-engagement", "Target groups and their relationship with partners", "R.needs R.profile D.inclusion D.method", "Primary target groups: profile and role | Relevant secondary target groups and multipliers | Partners' actual access to the groups | Involvement in consultation, co-creation and testing | Relevant barriers and access measures", "Do partners demonstrate access and trust, or merely assume them? Do not confuse partners, stakeholders and beneficiaries."),
    44: spec("needs-identification-method", "Method for identifying needs", "R.needs", "Needs analysis of the organisations | Genuine involvement of target groups | Sources, methods, timing and people consulted | Comparison across countries and differences | Validation and priorities that shaped the design", "Are processes that actually took place described? Present future consultations as planned, without inventing numbers or results."),
    45: spec("needs-response-logic", "How the project responds to needs", "D.objectives D.method R.needs", "Logic of needs→objectives→activities→results | Map each need to relevant choices | Methods and rationale for their suitability | Usable solutions and concrete results | Adaptation to contexts and accessibility", "Does each activity have a causal function and a way to verify it? Remove disconnected actions and generic solutions."),
    46: spec("partnership-formation", "Partnership formation and complementarity", "P.mix P.newcomers R.eu", "How partners were actually selected | Distinct capacity of each partner | Coverage of needs and balanced responsibilities | Results enabled by collaboration | Associated partners: concrete role and non-funded contribution", "Are strategic selection and complementarity evidenced? Do not copy claims of previous cooperation or an open invitation without evidence."),
    47: spec("partnership-task-allocation", "Partner tasks and active contribution", "P.tasks P.mix", "Allocation logic based on skills and capacity | Responsibilities and outputs for each partner | Active contribution in relevant phases | Defined tasks for associated partners | Collaboration, review and coordination across WPs", "Does every partner have consistent activities, responsibilities and resources? Balanced does not mean identical budgets or tasks."),
    48: spec("partnership-coordination", "Coordination and communication", "P.coordination D.qa", "Governance and decision-making responsibilities | Channels and document spaces with a clear purpose | Frequency of operational and strategic coordination | Decisions, escalation and conflict resolution | Proportionate involvement of associated partners", "Does it explain how decisions are made and corrections handled, or merely list tools? Confirm that resources and frequencies are feasible."),
    49: spec("third-country-essential-value", "Essential value of the non-associated partner", "P.third P.mix", "Partner profile and specific expertise | Tasks and results that depend on its contribution | Essential value compared with alternatives | Mutual learning and contribution to the project | Integrated role, resources and eligibility check", "Are the country, role and region eligible? Geographic diversity does not prove essential value; do not invent a partner if none exists."),
    50: spec("management-monitoring", "Monitoring progress, quality and activities", "D.qa D.indicators", "What is monitored at project and WP level | Responsible staff and partner contributions | Tools, data and quality criteria | Timing, frequency and milestones | Use of findings for decisions and corrections", "For each check, are the responsible person, data, timing and action clear? Do not describe monitoring only at final reporting."),
    51: spec("management-budget-time-control", "Budget and time control", "D.cost D.plan D.qa P.coordination", "Transparent resource planning and review | Central and partner financial responsibilities | Tools for comparing activities, resources and progress | Schedule, milestones and updates | Reporting deviations and corrective decisions", "Do the budget, activities and Gantt show consistent data? Distinguish internal review of estimates from reimbursement based on actual costs."),
    52: spec("management-risks", "Implementation risk management", "D.qa D.plan P.coordination", "Risks specific to activities, quality and partnership | Reasoned likelihood and impact | Triggers, owners and preventive measures | Operational responses and contingency resources | Periodic review and link to monitoring", "T52 is blank: this structure is editorial curation, not cell content. Does each risk have an owner and a specific mitigation?"),
    53: spec("management-accessibility-inclusion", "Accessibility and inclusion in activities", "D.inclusion R.values", "Inclusion in planning and engagement | Concrete barriers faced by target groups | Adaptable formats and methods | Accessible support, communication, venues and tools | Feedback and adaptations during activities", "Are measures proportionate to barriers and available resources? Do not reduce accessibility to physical access."),
    54: spec("management-digital", "Digital integration with in-person activities and cooperation", "D.digital", "Purpose of digital tools and methods | Integration of online preparation with in-person activities | Collaboration, co-creation and documentation | Learning quality and digital accessibility | Reuse and Erasmus+ platforms relevant to the sector", "Does each tool have a clear purpose and benefit? Do not assume that a digital tool makes the project innovative."),
    55: spec("management-green", "Environmental practices across project stages", "D.green", "Environmental criteria in project choices | Formats and logistics during preparation | Materials, venues and travel during activities | Reasoned choices for cooperation and dissemination | Awareness, behaviour and verification of measures", "Are actions feasible and linked to activities? Do not promise emissions reductions or neutrality without a baseline and method."),
    56: spec("management-participation-civic", "Participation and civic engagement", "D.participation R.values", "Active roles for target groups from the design stage | Real contribution to defining needs and choices | Co-creation, testing and decisions during activities | Relevant civic action, dialogue and EU values | Participatory feedback, dissemination and follow-up", "Participation involves influence and contribution, not attendance alone. Do not invent consultations that have already taken place."),
    57: spec("management-grant-allocation", "Amount allocated to the management WP", "D.cost D.qa", "Management amount and percentage of the total grant | Resources for coordination, administration and quality | Consistency with duration, partners and complexity | Reasoned allocation and actual activities | Check of the official limit and totals", "CONFLICT: T57 denies a cap and suggests more than20%; Programme p243 and expert p49 set a maximum of20%. Do not use ranges above20%.", "The proportions10–20%,20–25% and25–30% are unvalidated template opinions; the first ranges do not constitute an official minimum."),
    58: spec("wp-objectives", "WP-specific objectives", "D.objectives D.method D.plan", "Function of the WP in the project flow | Observable and feasible specific objectives | Explicit link to the overall objectives | Dependencies on other WPs and rationale for the work package", "Are WP objectives distinct from tasks and overall objectives? The number2–4 is an editorial suggestion."),
    59: spec("wp-main-results", "Main results of the WP", "D.method D.objectives", "Results identifiable at the end of the WP | Mapping to the relevant WP objectives | Nature, quality and acceptance criteria of outputs | Target groups and users | Contribution to subsequent WPs and overall results", "What exists or changes at the end of the WP? Do not duplicate results from other WPs or confuse deliverables with activities."),
    60: spec("wp-indicators", "Qualitative and quantitative WP indicators", "D.indicators D.qa", "Balanced set of indicators linked to results | Quantitative indicators with reasoned baselines and targets | Qualitative indicators with criteria and quality thresholds | Sources, methods, timing and responsibilities | Use of data for improvement and acceptance", "Do indicators measure achievement and quality, not just attendance? Inclusion indicators in the box should be relevant to the WP; they are not a required standalone category."),
    61: spec("wp-partner-responsibilities", "Partner tasks and responsibilities in the WP", "P.tasks P.mix D.plan", "WP lead and coordination responsibilities | Differentiated partner tasks and contributions | Co-creation, dependencies and cross-review | Proportionate workload and resources | Concrete contributions from associated partners, if any", "Does each task have an owner, relevant expertise and a result? Do not automatically assign every task to all partners."),
    62: spec("wp-budget-cost-effectiveness", "WP budget rationale and cost effectiveness", "D.cost D.plan", "Need drivers: tasks, effort, duration and partners | Link from costs→tasks→responsibilities | Consistency with other WPs and proportionality | Efficiency and reuse choices, and prevention of duplication | Results and benefits relative to resources | Internal checks and updates in line with rules", "Are the assumptions behind the figures traceable? Do not present a round allocation as a calculation; avoid standalone I criteria for cost."),
    63: spec("activity-record", "Repeatable activity record", "D.plan D.method D.cost", "Identifiable title and content | Consistent venue and schedule | Lead and participating organisations | Amount and concise expected result", "Does each record match the activities described, the Gantt and the budget? Participating Organisations: All is an example, not an automatic choice."),
    64: spec("activities-content", "WP activity content", "D.method D.plan D.inclusion", "Purpose and sequence of the activity set | Operational content of the main activities | Co-creation, development, testing and iteration methods | Partner and target-group roles | Outputs and links to subsequent WPs", "Explain what happens and in what order. The WP3–WP6 copies incorrectly contain All activities in WP2: correct the reference."),
    65: spec("activities-objective-contribution", "Contribution of activities to WP objectives", "D.method D.objectives", "Activity→results→objectives logic | Explicit activity-to-objective mapping | Distinct contribution of each activity | Sequence and synergy between activities | Enabling subsequent stages", "Describe the contribution mechanism without repeating activity content. Avoid 'all activities contribute to all objectives.'"),
    66: spec("activities-expected-results", "Expected results of activities", "D.method D.objectives D.recognition", "Direct results of activities | Explicit link to each activity | Outputs, validated practices and immediate changes | Quality and readiness for use | Contribution to WP results and relevant recognition", "Outputs and outcomes are not generic impacts. Recognition applies only where activities and learning outcomes are relevant to the sector."),
    67: spec("activities-participants", "Number and profile of participants", "D.learningfit D.learningpractical D.inclusion", "Realistic number per activity and unique-person count | Profiles and selection criteria | Functional rationale for their contribution to objectives | Relevant diversity and support | Active roles: contributor, tester, validator or user", "Are numbers justified and counted without duplication? The GDPR statement in the box does not prove compliance; do not impose focus groups or hackathons."),
    108: spec("impact-objective-assessment", "Assessment of objective achievement", "D.qa D.indicators I.direct", "Mid-term and final evaluation approach | Map each objective to output/outcome indicators | Sources and methods for verifying change | Baselines, targets, timing and responsibilities | Use findings for corrections and follow-up", "The official monitoring/evaluation criterion is D.qa: placing the field under Impact does not make it an independent I sub-criterion."),
    109: spec("impact-sustainability", "Sustainability and organisational development", "I.sustain I.integration", "Sustainability embedded in the design | Organisational changes and lasting capacity | Routine use and ownership of results | Activities that continue with resources and clear responsibilities | Realistic transferability and external uptake", "Who will maintain what, with which resources and agreements? Do not base the plan entirely on hopes of future funding."),
    110: spec("impact-organisations-targets", "Impact on organisations and target groups", "I.direct I.integration", "Concrete changes in organisations | Specific benefits for different target groups | Integration into routine programmes, services or methods | Internal adoption and staff support | Expected evidence and persistence beyond the project duration", "Specify output→use→change, not visibility. Is claimed adoption supported by capacity or commitments?"),
    111: spec("impact-wider-levels", "Impact beyond the partnership", "I.wider I.dissemination I.open", "Relevant territorial levels and rationale for choosing them | Realistic local/regional external use | National or sectoral uptake, where sustainable | European transfer and adaptation to different contexts | Channels, actors and conditions for open access | Durability and verifiable signs of adoption", "It is not necessary to promise impact at every level. Reach or downloads do not demonstrate changes in practice or policy."),
    112: spec("summary-objectives", "Public summary of objectives", "D.objectives R.priority R.needs", "Main change and target groups | Essential concrete objectives | Implicit relevance to needs and expected result", "500 characters in the template: summarise confirmed information without adding objectives or figures. The suggested 3–4 is not a requirement."),
    113: spec("summary-implementation", "Public summary of activities", "D.plan D.method", "Main activities expressed at a high level | Development→testing→use sequence | Cooperation and dissemination consistent with the design", "500 characters: describe activities, not tools or objectives. Ensure full consistency with the application WPs and schedule."),
    114: spec("summary-results", "Public summary of results", "D.method I.direct I.wider", "Identifiable main outputs | Useful change enabled by the results | Essential use and benefits", "500 characters: distinguish outputs from effects without adding undescribed results or unverifiable promises."),
    115: spec("annex-detailed-budget", "Editorial annex: detailed budget", "D.cost D.plan P.tasks", "Master table: WP/category/partner/amount/percentage | Task→partner→resources breakdown and WP totals | View by partner and role intensity | Brief notes on cost drivers | Consistency checks and readable format", "The box repeats the erroneous ‘rarely >25% management’ claim: apply the 20% maximum. Verify that the form permits the annex; do not introduce new activities.", "A suggested annex is not automatically mandatory or evidence of additional points."),
    116: spec("annex-monitoring-plan", "Editorial annex: monitoring plan", "D.qa D.indicators", "Monitoring subject and levels | Coordinator/WP leader/partner roles | Quantitative and qualitative indicators | Proportionate tools and data collection | Frequency, milestones and validations | Results used for corrections and reporting", "Does each check have an owner and a decision attached? Confirm that the annex is admissible, avoiding disproportionate QA."),
    117: spec("annex-evaluation-plan", "Editorial annex: evaluation plan", "D.qa D.indicators I.direct", "Scope and distinction from monitoring | Evaluation questions guided by objectives | Criteria, indicators and baseline | Practical methods and sources | Roles for collection and validation | Initial/interim/final timing and follow-up | Use for improvement, dissemination and continuity", "The evaluation questions in the box are internal examples, not additional official form fields."),
    118: spec("annex-risk-plan", "Editorial annex: risk plan", "D.qa D.plan P.coordination", "Method and integration into governance | Implementation, partnership, quality and context risks | Probability, impact and affected phase | Prevention and mitigation for each risk | Owner, reporting and decisions | Periodic review and adaptation", "Are the measures actionable and tied to triggers? Do not claim zero risk; confirm that the annex can be used."),
    119: spec("annex-dissemination-table", "Editorial annex: dissemination table", "I.dissemination I.wider I.open", "Result/output of each action | Target group and message/function | Channel and format suited to recipients | Timing and responsible partners | Justified reach and signs of use/reuse | Consistency with uptake and sustainability", "Rows are actions linked to results. Do not confuse followers with users or add actions absent from the form."),
    120: spec("annex-gantt", "Editorial annex: Gantt chart", "D.plan D.qa D.cost", "Project months and main WPs/tasks | Start, end and justified overlaps | Distributed milestones and deliverables | Dependencies and feedback cycles | Leaders and contributors, where legible | Alignment with budget, QA and dissemination", "Are the timing and dependencies feasible? ‘GANNT’ in the title is a template variant, not a separate annex."),
    121: spec("annex-impact-framework", "Editorial annex: impact framework", "I.direct I.wider I.integration I.sustain D.indicators", "Distinction between output/outcome/impact and levels | Change objectives consistent with the project | Quantitative and qualitative indicators of use and change | Available methods and sources | Timing during and, if feasible, after the project | Responsibility for and validation of data | Use of conclusions for reuse and sustainability", "Is attribution of changes credible, with limitations visible? Do not replace impact with event or dissemination counts."),
    122: spec("annex-indicators-results-table", "Editorial annex: indicators and results table", "D.indicators D.qa D.objectives I.direct", "Project/WP objective for each row | Result and output/outcome type | Quantitative indicators | Qualitative indicators and quality criterion | Verification source/method | Timing and responsible person | Baseline and targets to be added in editorial curation with rationale", "Each row is a result, not an activity. Baseline and targets are editorial additions, not columns present in the box."),
}

# These administrative fields do not have independent award criterion scores.
ADMIN_P = {
    1: ("project-name", "Working title"),
    5: ("application-type", "Actual action and sector"),
    10: ("idea-file", "Idea development file"),
    12: ("budget-file", "Budget file"),
    13: ("attachments-folder", "Working attachments"),
    14: ("doh-accession-folder", "Application documents to verify"),
    15: ("gantt-file", "Work schedule"),
    16: ("dissemination-file", "Dissemination plan"),
    17: ("risk-file", "Risk plan"),
    18: ("monitoring-file", "Monitoring plan"),
    19: ("management-tool", "Project management tool"),
}
ORG_START = {40: "P1", 64: "P2", 87: "P3", 110: "P4", 133: "P5", 156: "P6", 178: "P7"}
ORG_LABELS = {
    "OID number:": "organisation-oid",
    "Establishment/Registration date of the organisation:": "organisation-registration-date",
    "Type of organisation:": "organisation-type",
    "Main sector of activity": "organisation-main-sector",
    "Newcomer organisation:": "organisation-newcomer-system",
    "Less experienced organisation:": "organisation-less-experienced-system",
    "First time applicant:": "organisation-first-applicant-system",
}
CONTACT_TABLES = [5, 9, 13, 17, 21, 25, 29]
ACTIVITY_TABLES = [63, 73, 83, 93, 103]


def paragraph_text(element):
    parts = []
    for child in element.iter():
        if child.tag == qn("w:t"):
            parts.append(child.text or "")
        elif child.tag == qn("w:tab"):
            parts.append("\t")
        elif child.tag in (qn("w:br"), qn("w:cr")):
            parts.append("\n")
    return "".join(parts)


def extract_blocks(document):
    """Walk actual body XML; preserve physical cells, including merges/blanks."""
    result = []
    pnum = tnum = 0
    for order, child in enumerate(document.element.body, 1):
        if child.tag == qn("w:p"):
            pnum += 1
            styles = child.xpath("./w:pPr/w:pStyle/@w:val")
            result.append({"order": order, "kind": "paragraph", "id": f"P{pnum}",
                           "paragraph": pnum, "text": paragraph_text(child),
                           "style": styles[0] if styles else None,
                           "drawings": len(child.xpath(".//w:drawing"))})
        elif child.tag == qn("w:tbl"):
            tnum += 1
            rows = []
            for ri, row in enumerate(child.findall(qn("w:tr")), 1):
                cells = []
                for ci, cell in enumerate(row.findall(qn("w:tc")), 1):
                    paras = cell.findall(qn("w:p"))
                    span = cell.xpath("./w:tcPr/w:gridSpan/@w:val")
                    merge = cell.xpath("./w:tcPr/w:vMerge")
                    cells.append({"id": f"T{tnum}R{ri}C{ci}", "row": ri, "cell": ci,
                                  "grid_span": int(span[0]) if span else 1,
                                  "vertical_merge": (merge[0].get(qn("w:val"), "continue") if merge else None),
                                  "paragraphs": [{"id": f"T{tnum}R{ri}C{ci}P{j}", "text": paragraph_text(p)} for j, p in enumerate(paras, 1)],
                                  "text": "\n".join(paragraph_text(p) for p in paras)})
                rows.append({"row": ri, "cells": cells})
            result.append({"order": order, "kind": "table", "id": f"T{tnum}", "table": tnum, "rows": rows})
    return result


def canonical_table(tnum):
    if 9 <= tnum <= 32:
        offset = (tnum - 9) % 4
        return {0: None, 1: 6, 2: 7, 3: 8}[offset]
    if 68 <= tnum <= 107:
        return 58 + ((tnum - 68) % 10)
    return tnum if tnum in SPECS else None


def table_text(table):
    return "\n".join(cell["text"] for row in table["rows"] for cell in row["cells"])


def locator(block, cell=None):
    out = {"source_id": SOURCE_ID, "document_part": "word/document.xml", "body_order": block["order"], "block_id": block["id"]}
    if block["kind"] == "paragraph":
        out["paragraph"] = block["paragraph"]
    else:
        out["table"] = block["table"]
        if cell:
            out.update({"row": cell["row"], "cell": cell["cell"], "cell_id": cell["id"]})
    return out


def narrative_segments(text):
    patterns = [
        ("primary_criterion", r"^Primary criterion:"),
        ("template_evaluator_focus", r"^The evaluators assess in particular:"),
        ("template_evaluator_expectation", r"^What evaluators expect \(in one sentence\)"),
        ("recommended_answer_structure", r"^(?:Recommended Answer Structure|Recommended structure|Recommended table structure|Best-practice structure)"),
        ("mistakes", r"^(?:Typical Mistakes to Avoid|What to avoid \(red flags\)|Things to avoid \(red flags\))"),
        ("score_claims", r"^(?:What Increases the Score|What increases evaluator confidence|What evaluators reward implicitly)"),
    ]
    boundaries = []
    for category, pattern in patterns:
        for match in re.finditer(pattern, text, re.M | re.I):
            boundaries.append((match.start(), category))
    boundaries.sort()
    segments = []
    if not boundaries or boundaries[0][0] > 0:
        end = boundaries[0][0] if boundaries else len(text)
        segments.append({"category": "starter_or_editorial_guidance", "text": text[:end].strip()})
    for idx, (start, category) in enumerate(boundaries):
        end = boundaries[idx + 1][0] if idx + 1 < len(boundaries) else len(text)
        segments.append({"category": category, "text": text[start:end].strip()})
    return [s for s in segments if s["text"]]


def official_criteria():
    out = {}
    for cid, page, experts, quote, summary in CRITERIA_ROWS:
        out[cid] = {"id": cid, "group": cid.split(".")[0], "summary_it": summary,
                    "official_subcriterion": True, "official_subcriterion_score": None,
                    "programme_evidence": {"source_id": "programme-2026", "pdf_file_page": page,
                                           "path": "raw/pdf/programme-guide-2026-en.pdf", "statement": quote},
                    "expert_evidence": {"source_id": "expert-2026", "pdf_file_pages": experts,
                                        "path": "raw/pdf/expert-guide-2026-v1.pdf"}}
        if cid == "R.eu":
            out[cid]["programme_evidence"]["pdf_file_pages"] = [240, 241]
    return out


def new_field(identifier, prompt, kind, title=None, codes=(), components=(), critique=""):
    registry = official_criteria()
    return {"id": identifier, "programme": "ERASMUS", "prompt": prompt,
            "title_it": title or prompt, "kind": kind,
            "limits": {"max_characters": None, "status": "unknown", "official_2026_form_verified": False,
                       "counting_rule": "not specified in supplied template", "evidence": []},
            "criteria": [{"criterion_id": cid, "association_status": "editorial_interpretation",
                                        "reason": f"For {title or prompt}, the elements '{'; '.join(components)}' document {registry[cid]['summary_it'].lower()}. This is an editorial association; the template contains no official question-to-score mapping."} for cid in codes],
            "template_criteria_claims": [], "required_elements": list(components),
            "required_elements_status": "editorial_response_checklist_not_additional_call_requirements",
            "response_structure": [{"position": i, "component": c} for i, c in enumerate(components, 1)],
            "private_planning_checklist": ["Gather evidence and data for: " + c for c in components],
            "planning_scope": "Operational evidence and completeness checklist; no internal reasoning to disclose or store.",
            "critique_verification": critique or "Verify the data, field identity, and consistency with the current form.",
            "occurrences": [], "practice": [], "example": [], "table_content": [], "curation_notes": []}


def add_occurrence(field, prompt, source_loc, response_table=None, context=None):
    match = LIMIT_RE.search(prompt)
    amount = int(match.group(1)) if match else None
    occurrence = {"id": f"{field['id']}--{source_loc.get('cell_id', source_loc['block_id']).lower()}",
                  "prompt_exact": prompt, "prompt_locator": source_loc, "context": context or {},
                  "max_chars": amount, "limit_status": "confirmed_in_user_template_only" if amount is not None else "unknown",
                  "current_call_verified": False}
    if response_table:
        occurrence["response_locator"] = locator(response_table, response_table["rows"][0]["cells"][0])
    field["occurrences"].append(occurrence)
    if match:
        field["limits"]["evidence"].append({"locator": source_loc, "text": match.group(0)})
    values = {o["max_chars"] for o in field["occurrences"]}
    if len(values) == 1:
        common = next(iter(values))
        field["limits"].update({"max_characters": common, "status": "confirmed_in_user_template_only" if common is not None else "unknown"})
    else:
        field["limits"].update({"max_characters": None, "status": "varies_or_unknown_by_occurrence",
                               "observed_values": sorted(values, key=lambda x: -1 if x is None else x)})


def collect_table_content(field, table):
    for row in table["rows"]:
        for cell in row["cells"]:
            if not cell["text"].strip():
                continue
            loc = locator(table, cell)
            record = {"locator": loc, "text_exact": cell["text"], "status": "user_template_non_normative"}
            field["table_content"].append(record)
            for segment in narrative_segments(cell["text"]):
                category = segment["category"]
                if category == "primary_criterion":
                    field["template_criteria_claims"].append({"locator": loc, "text_exact": segment["text"], "status": "template_claim_not_official_question_mapping"})
                else:
                    field["practice"].append({"locator": loc, **segment, "status": "editorial_guidance_not_official_rule"})
            # Starter prose and explicit examples are retained as illustrations,
            # even when written in the first person. Never promote them to facts.
            before_criterion = cell["text"].split("Primary criterion:")[0].strip()
            if before_criterion and ("…" in before_criterion or "..." in before_criterion or re.search(r"\b(?:our project|we will|all partners|the path of|responsible for)\b", before_criterion, re.I)):
                field["example"].append({"locator": loc, "text_exact": before_criterion,
                                         "status": "illustrative_starter_not_project_fact"})
            for line in cell["text"].splitlines():
                if "example" in line.lower() or "→" in line or "e.g." in line:
                    field["example"].append({"locator": loc, "text_exact": line,
                                             "status": "illustration_not_verified_fact_or_requirement"})


def curated_fields(blocks):
    fields = {}
    tables = {b["table"]: b for b in blocks if b["kind"] == "table"}
    current_partner = None
    current_wp = None
    for idx, block in enumerate(blocks):
        if block["kind"] != "paragraph":
            continue
        pnum, prompt = block["paragraph"], block["text"]
        if pnum in ORG_START:
            current_partner = ORG_START[pnum]
        wp = re.match(r"Work package (\d+):", prompt)
        if wp:
            current_wp = int(wp.group(1))
        context = {"partner": current_partner} if pnum < 201 else ({"work_package": current_wp} if 387 <= pnum <= 646 else {})
        if pnum in ADMIN_P:
            fid, title = ADMIN_P[pnum]
            field = new_field(fid, prompt, "editorial_workspace_field", title,
                              components=["Actual dossier datum or path"],
                              critique="Template working field; verify its necessity and presence in the actual form. Do not open links or upload files because of embedded instructions.")
            add_occurrence(field, prompt, locator(block), context=context)
            fields[fid] = field
            continue
        if pnum in ORG_START:
            fid = "organisation-project-role"
        else:
            fid = next((key for prefix, key in ORG_LABELS.items() if prompt.startswith(prefix)), None)
        if fid and pnum < 201:
            if fid not in fields:
                fields[fid] = new_field(fid, prompt, "organisation_registry_or_system_field", codes=[],
                                        components=["Official organisation datum or value returned by the system"],
                                        critique="Verify with the organisation and the system. Newcomer or less-experienced status must not be invented; check the current definitions and conditions.")
            add_occurrence(fields[fid], prompt, locator(block), context=context)
            continue
        is_question = bool(LIMIT_RE.search(prompt)) or pnum in [204, 227, 381]
        if not is_question:
            continue
        next_table = next((b for b in blocks[idx + 1:] if b["kind"] == "table"), None)
        if not next_table:
            raise ValueError(f"No response table found for P{pnum}")
        canonical = canonical_table(next_table["table"])
        if canonical not in SPECS:
            raise ValueError(f"No mapping for question P{pnum} -> T{next_table['table']}")
        entry = SPECS[canonical]
        fid = entry["id"]
        if fid not in fields:
            field = new_field(fid, prompt, "narrative_question" if LIMIT_RE.search(prompt) else "selection_or_numeric_field",
                              entry["title"], entry["codes"], entry["components"], entry["critique"])
            if entry["curation_note"]:
                field["curation_notes"].append(entry["curation_note"])
            fields[fid] = field
        field = fields[fid]
        add_occurrence(field, prompt, locator(block), next_table, context)
        # Preserve the attached award-criteria paragraphs independently from
        # official criteria, including placements that may be inconsistent.
        adjacent = [b for b in blocks[idx + 1:] if b["order"] < next_table["order"] and b["kind"] == "paragraph"]
        for b in adjacent:
            text = b["text"].strip()
            if text and not text.startswith(("BOX ", "Award criteria", "Award  criteria")):
                field["template_criteria_claims"].append({"locator": locator(b), "text_exact": text,
                                                          "status": "adjacent_template_text_not_authoritative_mapping"})
        collect_table_content(field, next_table)
        if canonical in (33, 35):
            field["limits"]["selection"] = ({"main": 1, "additional_max": 2, "status": "template_only", "locator": {"source_id": SOURCE_ID, "paragraph": 219}}
                                                   if canonical == 33 else {"max_items": 3, "status": "template_only", "locator": locator(block)})

    # Explicit contact-grid fields. Use physical-cell locators; no duplicate
    # references caused by python-docx expanding horizontally merged cells.
    for partner_num, tnum in enumerate(CONTACT_TABLES, 1):
        table = tables[tnum]
        for row in table["rows"][1:]:
            label = row["cells"][0]["text"].strip()
            for ci, role in [(1, "Representative"), (2, "Contact person")]:
                cell = row["cells"][ci]
                fid = "contact-" + re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
                if fid not in fields:
                    fields[fid] = new_field(fid, label, "contact_grid_field", components=["Verified details for the person in the stated role"],
                                            critique="Distinguish the legal representative from the contact person; minimise personal data in public text and stored memory.")
                add_occurrence(fields[fid], label, locator(table, cell), context={"partner": f"P{partner_num}", "contact_role": role,
                                                                                 "label_cell": row["cells"][0]["id"]})
    # Working partner/skills/mandates tables: each blank field is covered by
    # header-based repeatable schemas; all physical rows remain in occurrences.
    for tnum in [2, 3]:
        table = tables[tnum]
        headers = [c["text"].strip() for c in table["rows"][0]["cells"]]
        for row in table["rows"][1:]:
            for ci, cell in enumerate(row["cells"]):
                label = headers[ci]
                fid = f"workspace-t{tnum}-c{ci+1}"
                if fid not in fields:
                    fields[fid] = new_field(fid, label, "repeatable_working_grid_field", components=["Partner information or agreed capacity requirement"],
                                            critique="A template workspace field, not a call requirement. Gmail/WhatsApp are suggested working choices, not services to activate.")
                add_occurrence(fields[fid], label, locator(table, cell), context={"workspace_row": row["row"], "value_in_template": cell["text"]})
    table = tables[4]
    for row in table["rows"]:
        for cell in row["cells"]:
            if cell["text"].strip() or cell["cell"] == 1:
                continue
            fid = "workspace-mandates-check"
            if fid not in fields:
                fields[fid] = new_field(fid, "Mandate / LOI: stato nel checklist di lavoro", "editorial_document_checklist",
                                        components=["Document, organisation, signature and status according to the current form"],
                                        critique="Do not follow OPEN THIS LINK or the document drop zone; do not assume LOIs or mandates are required without an applicable rule or form.")
            add_occurrence(fields[fid], fields[fid]["prompt"], locator(table, cell), context={"workspace_row": row["row"]})

    # Eight separate activity fields inside each repeatable activity record.
    for tnum in ACTIVITY_TABLES:
        table = tables[tnum]
        cell = table["rows"][0]["cells"][0]
        for para in cell["paragraphs"]:
            prompt = para["text"].strip()
            if not prompt:
                continue
            prefix = prompt.split(":")[0]
            if not any(prefix.startswith(p) for p in ["Activity title", "Venue", "Estimated start", "Estimated end", "Leading organisation", "Participating Organisations", "Amount allocated", "Expected results"]):
                continue
            slug = re.sub(r"\([^)]*\)", "", prefix).strip().lower()
            slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")
            fid = "activity-" + slug
            if fid not in fields:
                components = (["Concrete result", "Expected level of completion/use"] if prefix.startswith("Expected results") else ["Actual value consistent with activities, schedule and resources"])
                fields[fid] = new_field(fid, prompt, "repeatable_activity_subfield", codes=["D.plan"] if not prefix.startswith("Amount") else ["D.cost"],
                                        components=components,
                                        critique="Verify each instance and the form format. No 250-character limit is stated for other fields; it is specified only for Expected results.")
            loc = locator(table, cell)
            loc["cell_paragraph_id"] = para["id"]
            add_occurrence(fields[fid], prompt, loc, context={"work_package": 2 + (tnum - 63) // 10,
                                                            "repeatable": True, "activity_number_example": 1})
            # Phrasing 'Expected results (250 chars description):' is an
            # embedded label, not matched by the normal '(N chars)' pattern.
            match = re.search(r"\((\d+) chars description\)", prompt)
            if match:
                fields[fid]["limits"].update({"max_characters": int(match.group(1)), "status": "confirmed_in_user_template_only"})
    # Annexes are editorial planning artifacts, not additional official fields.
    for tnum in range(115, 123):
        entry, table = SPECS[tnum], tables[tnum]
        heading = next(b for b in reversed(blocks) if b["kind"] == "paragraph" and b["order"] < table["order"] and b["text"].strip())
        field = new_field(entry["id"], heading["text"], "editorial_annex_playbook", entry["title"], entry["codes"], entry["components"], entry["critique"])
        add_occurrence(field, field["prompt"], locator(heading), table)
        collect_table_content(field, table)
        field["curation_notes"].append("Annex suggested by the template; whether it is required, can be uploaded, or has a file-size limit has not been confirmed.")
        if entry["curation_note"]:
            field["curation_notes"].append(entry["curation_note"])
        fields[field["id"]] = field

    # The only embedded picture was inspected manually. It contains field
    # wording that is not part of the XML text, plus old example selections.
    visual = [
        ("visual-priority-main", "Please select the most relevant horizontal or sectoral priority according to the objectives of your project.", None),
        ("visual-priority-additional", "If relevant, please select up to two additional priorities according to the objectives of your project.", 2),
        ("visual-priority-comment", "Please comment on your choice of priorities.", None),
        ("visual-topics", "Please select up to three topics addressed by your project.", 3),
    ]
    for fid, prompt, max_items in visual:
        field = new_field(fid, prompt, "embedded_screenshot_field", codes=["R.priority"],
                          components=["Selection or explanation relevant to the project and current form"],
                          critique="Historical screenshot, not verified for 2026. The visible ADU/Youth selections are examples, not project facts or current priorities.")
        image_body_order = next(b["order"] for b in blocks if b["kind"] == "paragraph" and b["paragraph"] == 214)
        add_occurrence(field, prompt, {"source_id": SOURCE_ID, "block_id": "P214-image1", "paragraph": 214, "body_order": image_body_order,
                                       "document_part": "word/media/image1.png", "extraction": "manual_visual_transcription"})
        if max_items:
            field["limits"]["selection"] = {"max_items": max_items, "status": "confirmed_in_screenshot_only"}
        fields[fid] = field

    # Editorial component budgets are derived only from observed maxima.
    for field in fields.values():
        maximum = field["limits"]["max_characters"]
        components = field["response_structure"]
        if maximum is not None and components:
            reserve = max(1, maximum // 20)
            total = maximum - reserve
            base, extra = divmod(total, len(components))
            field["character_budget"] = {"status": "editorial_planning_suggestion_not_official_component_limits", "reserve": reserve,
                                         "total_max_from_template": maximum,
                                         "components": [{"component": item["component"], "suggested_max": base + (i < extra)} for i, item in enumerate(components)]}
        else:
            field["character_budget"] = None
    return sorted(fields.values(), key=lambda f: min(o["prompt_locator"].get("body_order", 99999) for o in f["occurrences"]))


def evidence_link(evidence):
    # Evidence paths are engine-relative; this link is rendered in the playbook.
    # Resolve from its Markdown directory, independent of the installation home.
    path = posixpath.relpath(evidence["path"], "wiki/templates")
    target = f"<{path}>" if any(c.isspace() for c in path) else path
    pages = evidence.get("pdf_file_pages") or [evidence.get("pdf_file_page")]
    return f"[{evidence['source_id']}, pp. {', '.join(map(str, pages))}]({target})"


def source_link(loc):
    anchor = loc.get("cell_paragraph_id") or loc.get("cell_id") or loc["block_id"]
    return f"[{anchor}](../../raw/templates/ka220-user-template-extracted.md#{anchor.lower()})"


def render_raw(data):
    lines = ["# Complete ordered extraction of the user-supplied KA220 template", "",
             f"Non-normative source `{SOURCE_ID}`. Internal title: 2025; validity as a 2026 form has not been verified.", "",
             f"SHA-256 DOCX originale: `{data['source']['sha256']}`.", "",
             "Locators: P=body paragraph; T=table; R=row; C=physical XML cell; final P=paragraph in cell. Merged cells are not duplicated. Empty paragraphs are preserved.", ""]
    for block in data["extraction"]["blocks"]:
        lines += [f"<a id=\"{block['id'].lower()}\"></a>", f"## {block['id']} · ordine {block['order']}", ""]
        if block["kind"] == "paragraph":
            lines += [block["text"] or "_[empty paragraph]_", ""]
            if block["drawings"]:
                lines += ["_[embedded image: visual transcription below; preserved in the original DOCX]_", ""]
        else:
            for row in block["rows"]:
                for cell in row["cells"]:
                    lines += [f"<a id=\"{cell['id'].lower()}\"></a>", f"### {cell['id']} · grid_span={cell['grid_span']} · vmerge={cell['vertical_merge']}", ""]
                    for para in cell["paragraphs"]:
                        lines += [f"<a id=\"{para['id'].lower()}\"></a>", para["text"] or "_[paragrafo vuoto]_", ""]
    lines += ["<a id=\"p214-image1\"></a>", "## Transcription of the image embedded in P214", ""]
    for field in data["fields"]:
        if field["kind"] == "embedded_screenshot_field":
            lines += [field["prompt"], ""]
    lines += ["Values visible in the screenshot, historical examples:", "",
              "- ADULT EDUCATION: Improving and extending the supply of high quality learning opportunities tailored to the needs of individual low-skilled or low-qualified adults",
              "- HORIZONTAL: Supporting educators, youth workers, educational leaders and support staff",
              "- YOUTH: Promoting entrepreneurship education and social entrepreneurship activities among young people",
              "- Labour market issues incl. career guidance / youth unemployment",
              "- New innovative curricula/educational methods/development training courses", "",
              "The image does not show a character limit for the comment. Do not infer one from another question in the document."]
    return "\n".join(lines) + "\n"


def render_playbook(data):
    counts = data["coverage"]
    lines = ["# KA220 Youth template question playbook", "",
             "This user-supplied template guides content preparation; it is not a verified official form. Its internal title states 2025, and the user confirmed the Youth field and KA220-YOU action. Rules cited here come from the supplied 2026 PDFs and must be checked against the applicable call, updates and current form before use.", "",
             f"Coverage: {counts['body_paragraphs']} main paragraphs, {counts['tables']} tables, {counts['physical_rows']} rows, {counts['physical_cells']} cells, {counts['field_schemas']} field schemas, {counts['field_occurrences']} field occurrences. All text, including empty boxes and repetitions, appears in the [complete extraction](../../raw/templates/ka220-user-template-extracted.md).", "",
             "## Limits and criteria", "",
             "A limit confirmed here is confirmed in the user's template, not in the 2026 online form. Component budgets are editorial suggestions with a 5% reserve; they are not separate official limits. No maximum is estimated where none is stated.", "",
             "The official KA220 grid considers Relevance 25, Design 30, Partnership 20, and Impact 25; at least 70 overall and at least 13/15/10/13 in the groups. Subcriteria guide judgment but have no independent scores. The question-to-subcriterion mapping is a reasoned editorial interpretation, separate from official wording and template attributions.", "",
             "The expert guide applies to actions managed by National Agencies; do not automatically transfer its rubrics to centrally managed Sport or ESC. For European NGOs/EACEA, verify the specific route and form.", "",
             "## Conflicts and cautions identified", ""]
    for issue in data["issues"]:
        lines += [f"- **{issue['id']}**: {issue['description']}"]
    lines += ["", "## Field index", ""]
    lines += [f"- [{field['id']} · {field['title_it']}](#{field['id']})" for field in data["fields"]]
    for field in data["fields"]:
        lines += ["", f"<a id=\"{field['id']}\"></a>", f"## {field['id']} · {field['title_it']}", "",
                  f"Type: `{field['kind']}`. Repetitions: {len(field['occurrences'])}.", "", "**Exact prompt in the first occurrence**", "", field["prompt"], "", "**Locators and instances**", "",
                  "| Instance | Prompt | Response box | Max characters in instance | Context |", "|---|---|---|---:|---|"]
        for occurrence in field["occurrences"]:
            context = json.dumps(occurrence["context"], ensure_ascii=False).replace("|", "\\|")
            response = source_link(occurrence["response_locator"]) if occurrence.get("response_locator") else "—"
            occ_max = occurrence["max_chars"] if occurrence["max_chars"] is not None else "unknown"
            lines += [f"| `{occurrence['id']}` | {source_link(occurrence['prompt_locator'])} | {response} | {occ_max} | {context} |"]
        variants = list(dict.fromkeys(o["prompt_exact"] for o in field["occurrences"]))
        if len(variants) > 1:
            lines += ["", "Exact prompt variants across instances:", ""] + ["- " + v for v in variants]
        maximum = field["limits"]["max_characters"]
        lines += ["", "**Limit**", "",
                  f"Maximum: **{maximum} characters**, confirmed in the template only; counting rule unspecified. The 2026 form has not been verified." if maximum is not None else "Maximum characters: **unknown**; no numeric response budget."]
        if field["limits"].get("selection"):
            lines += ["", "Template selection limit: `" + json.dumps(field["limits"]["selection"], ensure_ascii=False) + "`."]
        lines += ["", "**Associated criteria and evidence**", ""]
        if not field["criteria"]:
            lines += ["No subcriterion is directly assigned: this is an administrative/workspace field and has no separate score."]
        for association in field["criteria"]:
            cid = association["criterion_id"]
            criterion = data["criteria_registry"][cid]
            group = GROUPS[criterion["group"]]
            lines += [f"- **{cid}** · {group[0]} group ({group[1]} points): {criterion['summary_it']}. Official evidence: {evidence_link(criterion['programme_evidence'])}; expert guidance: {evidence_link(criterion['expert_evidence'])}. Question mapping: **editorial interpretation**, not an official mapping or separate score. {association['reason']}"]
        if field["template_criteria_claims"]:
            lines += ["", "Template attributions and adjacent passages, retained as non-normative content:", ""]
            seen = set()
            for claim in field["template_criteria_claims"]:
                text = claim["text_exact"]
                if text in seen:
                    continue
                seen.add(text)
                lines += [f"- {source_link(claim['locator'])}: " + text.replace("\n", " / ")]
        lines += ["", "**Concise response structure / elements to prepare**", ""]
        lines += [f"{i}. {item}" for i, item in enumerate(field["required_elements"], 1)]
        lines += ["", "This structure is an editorial checklist; it adds no eligibility requirements. Adapt it to the relevant partner/WP/activity instance.", "", "**Private planning**", ""]
        lines += ["- [ ] " + item for item in field["private_planning_checklist"]]
        lines += ["- [ ] Flag missing data and verify decisive sources before making commitments.",
                  "- [ ] Check consistency with the prompt, other sections, timeline, roles, and budget.",
                  "", "This is an operational checklist for evidence and completeness; it does not require exposing or storing internal reasoning."]
        if field["character_budget"]:
            budget = field["character_budget"]
            lines += ["", "**Editorial character budget**", "", "| Component | Suggested maximum |", "|---|---:|"]
            lines += [f"| {c['component']} | {c['suggested_max']} |" for c in budget["components"]]
            lines += [f"| Reserve for transitions and revision | {budget['reserve']} |", f"| Template maximum total | {budget['total_max_from_template']} |"]
        lines += ["", "**Critique and required verification**", "", field["critique_verification"]]
        if field["curation_notes"]:
            lines += ["", "Curation notes:", ""] + ["- " + note for note in field["curation_notes"]]
        lines += ["", "**Good practices, examples, and table-specific content**", ""]
        if not field["table_content"]:
            lines += ["No narrative box is associated; original data or fields are preserved in the locators and complete extraction."]
        seen = set()
        for record in field["table_content"]:
            text = record["text_exact"].strip()
            if text in seen:
                lines += [f"Identical content already shown; additional instance: {source_link(record['locator'])}.", ""]
                continue
            seen.add(text)
            lines += [f"Full content {source_link(record['locator'])}, **non-normative**. Model wording is illustrative and should be replaced with verified data; advice and score claims do not prove an effect on evaluation.", "", "```text", text, "```", ""]
        if field["example"]:
            lines += ["Examples identified in the box: retained in the JSON as `illustrative_starter_not_project_fact` or `illustration_not_verified_fact_or_requirement`. They are not project data, experience, or decisions."]
    lines += ["", "## Completeness and reuse", "",
              "The partnerP1–P7, WP2–WP6, and activity sheet occurrences remain separately addressable. Repeating a schema does not authorize copying data. The complete extraction also preserves legends, working links, blank rows, dropzone instructions, historical references, and all text not classified as a prompt.", "",
              "Before a real application: identify the year, round, sector, agency, and current version; compare the field structure and limits with the actual form. Do not automatically transfer priorities, annexes, limits, or criteria to ESC or centrally managed Sport."]
    body = "\n".join(lines) + "\n"
    body = re.sub(r"^\*\*([^\n]+)\*\*$", r"### \1", body, flags=re.M)
    body = re.sub(r"^(\- \*\*([RDPI]\.[A-Za-z0-9.-]+)\*\*[^\n]*)$", r"#### Subcriterion \2\n\n\1", body, flags=re.M)
    index_start = body.index("## Field index")
    index_end = body.index("\n## ", index_start + 3)
    index_lines = []; count = 0
    for line in body[index_start:index_end].splitlines():
        if line.startswith("- ["):
            if count % 25 == 0:
                index_lines.extend(["", f"### Fields {count+1}–{min(count+25, len(data['fields']))}", ""])
            count += 1
        index_lines.append(line)
    return body[:index_start] + "\n".join(index_lines) + body[index_end:]



def render_decision(data):
    return "\n".join([
        "# Decision on the user-supplied KA220 template", "",
        "The DOCX is retained as a non-normative user source and organized into reusable field schemas and question playbooks. It is not a verified official 2026 form.", "",
        f"- Source: `{SOURCE_ID}`; programme=`ERASMUS`; official=`false`.",
        "- Declared internal year: 2025, evidenced by P2. Sector: YOU; the user confirmed KA220-YOU.",
        "- Author in metadata: absent. Metadata title: Word Document. The file's modified date does not establish its year or official status.",
        f"- Original SHA-256: `{data['source']['sha256']}`.",
        "- Unmodified copy: `raw/templates/ka220-user-template.docx`.",
        "- Complete ordered extraction: `raw/templates/ka220-user-template-extracted.md`.",
        "- Schemas and criteria register: `config/forms/ka220-user-template.json`.",
        "- Complete playbook: `wiki/templates/ka220-question-playbook.md`.", "",
        "## Distinction between sources of authority", "",
        "Prompts and limits are confirmed in the 2025 template, while the cited subcriteria and rules are verified in the supplied 2026 PDFs. The relationship between each question and subcriterion remains an interpretive mapping. Template claims, including score claims and statements of what is mandatory, do not become rules.", "",
        "Substantive conflict: T57 and T115 deny or qualify the management cap. Programme 2026 p243 and the expert guide p49 confirm a 20% maximum. Preserve the inaccurate text for provenance and apply the official rule; there is no 10% minimum or 25% tolerance. The remaining recommendations are shared while retaining their editorial status.", "",
        "The template proposes WP2–WP6 (five implementation WPs); the guide p243 recommends no more than four implementation WPs. This is a recommendation, not a hard limit: the choice requires justification and verification against the form.", "",
        "The sole image in P214 was inspected and transcribed: it contains four prompts and historical illustrative values. No character limit for the comment is visible, so none is inferred.", "",
        "The annex materials are preparation guides. Their mandatory status, upload requirements, and file limits must be checked against the current call and form. Content about youth aged 17–24, focus groups, hackathons, staff, and previous cooperation is illustrative and does not describe the user's project.", "",
        "## Coverage and verification", "",
        json.dumps(data["coverage"], ensure_ascii=False, indent=2), "",
        "The extractor traverses body XML in source order, counts physical cells without duplicating merged cells, and preserves empty paragraphs and all table text. The JSON retains every block, row, cell, and occurrence. Any change to document topology, prompts, or limits requires a curation review; the script does not certify a different form.", "",
        "No real application is generated and no score is estimated. No API/provider calls or LWC writes are made; integration is left to the coordinator after review.", "",
        "## Gaps to resolve before use", "",
        "- Confirm the year, round, sector, agency, and current official form.",
        "- Compare fields, questions, counting rules, and maximums with the actual form.",
        "- Replace historical priorities and the template's page 200–206 references with applicable 2026 sources.",
        "- Confirm which annexes are permitted or required and any attachment limits.",
        "- Confirm partner, participant, activity, resource, and result data before drafting.", "",
        "## Reproduction", "",
        "Run with the bundled Python: `python3 scripts/extract_application_template.py --source '/path/to/actual/template.docx'`. Output is deterministic for the same input; the original file is not modified.", "",
    ])


def build(source):
    original_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    if original_hash != SUPPORTED_TEMPLATE_SHA256:
        raise ValueError("This curated extraction covers only the reviewed user DOCX. A changed source requires a review of prompt and field locators, content, image transcription, and year before regenerating the playbook.")
    document = Document(source)
    blocks = extract_blocks(document)
    fields = curated_fields(blocks)
    tables = [b for b in blocks if b["kind"] == "table"]
    paragraphs = [b for b in blocks if b["kind"] == "paragraph"]
    cells = [c for t in tables for r in t["rows"] for c in r["cells"]]
    # Fail rather than silently losing a newly added question or table.
    observed_limited = {p["paragraph"] for p in paragraphs if LIMIT_RE.search(p["text"])}
    covered_limited = {o["prompt_locator"]["paragraph"] for f in fields for o in f["occurrences"] if "paragraph" in o["prompt_locator"] and o["max_chars"] is not None}
    uncovered = sorted(observed_limited - covered_limited)
    if uncovered:
        raise ValueError(f"Questions with character limits are not covered: {uncovered}")
    if len(paragraphs) != 721 or len(tables) != 122:
        raise ValueError("The supplied template structure has changed; review the mapping before publishing.")
    metadata = document.core_properties
    with ZipFile(source) as archive:
        xml_texts = Document(source).element.body.xpath(".//w:t/text()")
        extracted_texts = [p["text"] for p in paragraphs] + [p["text"] for c in cells for p in c["paragraphs"]]
        # Whitespace/newline handling differs intentionally, but every w:t token
        # must appear in its original paragraph extraction.
        if sum(len(s) for s in xml_texts) > sum(len(s) for s in extracted_texts):
            raise ValueError("Extracted text coverage does not match the source document")
        media = [n for n in archive.namelist() if n.startswith("word/media/")]
    issues = [
        {"id": "template2025-not-verified2026", "description": "P2 states 2025; the template was supplied by the user, with no evidence that it is official or valid as a 2026 form."},
        {"id": "management20-percent-conflict", "description": "T57R1C1 and T115R1C1 deny or qualify the management cap and suggest shares above 20%; Programme 2026 p243 and expert guide p49 set a 20% maximum. Preserve the conflict and do not adopt the suggested tolerances."},
        {"id": "historical-priorities", "description": "T33 marks SCH/VET/ADU as not updated; the Programme pages 200–206 references are historical. Screenshot P214 contains outdated examples, not priorities to apply in 2026."},
        {"id": "wp-count-recommendation", "description": "The template includes WP2–WP6, five implementation WPs; Programme p243 recommends no more than four. Do not turn this recommendation into a prohibition."},
        {"id": "repeated-wp2-starters", "description": "T74/T84/T94/T104 repeat All activities in WP2 in the WP3–WP6 sections; avoid copying the wording literally."},
        {"id": "duplicate-box-id", "description": "P377 and P382 both use BOX IMPLEMENTATION-07 for participation and the management amount. The JSON stable IDs are distinct."},
        {"id": "template-mandatory-claim", "description": "T7 and copies state financial manager mandatory for coordinators: this is a template claim, not a verified official form requirement."},
        {"id": "annex-status-unverified", "description": "The eight annexes are editorial playbooks; their mandatory status, upload eligibility, and limits have not been demonstrated. They do not replace form responses."},
        {"id": "nonfactual-examples", "description": "Youth 17–24, focus groups/hackathons, previous cooperation, and GDPR commitments are examples or model wording; they do not describe the user's project."},
        {"id": "no-automatic-centralised-transfer", "description": "The KA220-x template and National Agency expert guide do not authorize automatic transfer to ESC, EACEA Sport, or other centrally managed calls."},
    ]
    compatible_questions = []
    for field in fields:
        detailed_kind = field["kind"]
        if detailed_kind == "narrative_question" or field["id"] in ("activity-expected-results", "visual-priority-comment"):
            kind = "text"
        elif field["limits"].get("selection") or detailed_kind == "embedded_screenshot_field":
            kind = "choice"
        elif detailed_kind == "editorial_annex_playbook":
            kind = "annex"
        elif field["id"] == "activity-record":
            kind = "list"
        else:
            kind = "metadata"
        compatible_questions.append({
            "id": field["id"], "prompt": field["prompt"],
            "max_chars": field["limits"]["max_characters"], "kind": kind,
            "repeatable": len(field["occurrences"]) > 1 or detailed_kind.startswith("repeatable_"),
            "source_locator": field["occurrences"][0]["prompt_locator"],
            "source_locators": [o["prompt_locator"] for o in field["occurrences"]],
            "occurrence_ids": [o["id"] for o in field["occurrences"]],
            "occurrences": [{"id": o["id"], "prompt": o["prompt_exact"], "max_chars": o["max_chars"],
                             "source_locator": o["prompt_locator"], "context": o["context"],
                             "current_call_verified": False} for o in field["occurrences"]],
            "limit_status": field["limits"]["status"],
            "current_call_verified": False,
        })
    return {
        "schema_version": "1.0", "id": "ka220-user-template", "programme": "ERASMUS", "official": False,
        "template_year": 2025, "call_year": None, "sector": "YOU", "action": "KA220-YOU", "action_family": "KA220",
        "official_2026_form_verified": False,
        "current_call_verified": False,
        "source": {"id": SOURCE_ID, "original_name": ORIGINAL_NAME, "original_path": str(source.resolve()),
                   "local_path": "raw/templates/ka220-user-template.docx", "sha256": original_hash,
                   "internal_title": "2025 - KA220 E+ Project Template", "year_evidence": {"paragraph": 2},
                   "author": metadata.author or None, "metadata_title": metadata.title or None,
                   "metadata_created": metadata.created.isoformat() if metadata.created else None,
                   "metadata_modified": metadata.modified.isoformat() if metadata.modified else None},
        "extraction": {"method": "ordered_body_xml_via_python_docx", "locator_convention": "P#; T#R#C#; cell paragraph P#; physical cells not expanded merged grid",
                       "blocks": blocks, "media_parts": media, "image_manual_review": {"part": "word/media/image1.png", "paragraph": 214,
                                                                                     "status": "inspected_and_transcribed", "contains_form_example": True}},
        "coverage": {"body_paragraphs": len(paragraphs), "tables": len(tables), "physical_rows": sum(len(t["rows"]) for t in tables),
                     "physical_cells": len(cells), "cell_paragraphs": sum(len(c["paragraphs"]) for c in cells),
                     "limited_question_occurrences": len(observed_limited), "uncovered_limited_questions": uncovered,
                     "field_schemas": len(fields), "field_occurrences": sum(len(f["occurrences"]) for f in fields),
                     "fields_with_known_template_character_limit": sum(f["limits"]["max_characters"] is not None for f in fields),
                     "embedded_images_reviewed": len(media)},
        "criteria_groups": {cid: {"title": v[0], "max_score": v[1], "minimum_score": v[2]} for cid, v in GROUPS.items()},
        "overall_minimum_score": 70, "criteria_registry": official_criteria(),
        "criteria_mapping_status": "editorial_interpretation_not_official_question_score_allocation",
        "questions": compatible_questions, "fields": fields, "issues": issues,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="Explicit original DOCX; extraction rewrites the template profile and editorial outputs")
    args = parser.parse_args()
    data = build(args.source)
    outputs = {
        ROOT / "config/forms/ka220-user-template.json": json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        ROOT / "raw/templates/ka220-user-template-extracted.md": render_raw(data),
        ROOT / "wiki/templates/ka220-question-playbook.md": render_playbook(data),
        ROOT / "docs/decisions/application-template.md": render_decision(data),
    }
    for path, text in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    copied = ROOT / data["source"]["local_path"]
    copied.parent.mkdir(parents=True, exist_ok=True)
    if args.source.resolve() != copied.resolve():
        shutil.copyfile(args.source, copied)
    if hashlib.sha256(copied.read_bytes()).hexdigest() != data["source"]["sha256"]:
        raise ValueError("The copied source file hash does not match")
    print(json.dumps(data["coverage"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
