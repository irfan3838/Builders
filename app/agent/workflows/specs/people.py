from app.agent.workflows.spec import Workflow as W

M = "people"
_ASK = "Read the proposal's 'say' text and ask for confirmation. Stop."
WORKFLOWS = [
    W("find_people", M, "Who is someone / who reports to whom: 'who is Rohan', 'my team', 'who reports to me', "
      "'Sales team'.", ("find_people",), ("Call find_people.", "Speak name, role and team; at most five people.")),
    W("leave_balance", M, "Leave balance: 'meri kitni chutti bachi hai', 'leave balance', 'how many CL left'.",
      ("get_leave_balance",), ("Call get_leave_balance.", "Speak each leave type left.")),
    W("leave_list", M, "Leave requests list or status: 'meri leave ka status', 'pending leave requests', 'who is "
      "on leave', 'Neha ki leave dikhao'.", ("list_leave_requests",),
      ("Call list_leave_requests (mine, awaiting_my_decision or team).", "Speak at most three with dates and state.")),
    W("leave_request", M, "Apply for leave for myself: 'kal chutti chahiye', 'I need leave on Monday and Tuesday', "
      "'3 din ki chutti'.", ("get_leave_balance", "propose_leave"),
      ("Resolve dates ('kal', 'parson', 'next Monday') from today and say them back. Vague dates ('early "
       "December'): ask_choice with 3-5 concrete dates.", "Check get_leave_balance if the type may be short.",
       "Call propose_leave.", _ASK)),
    W("leave_decision", M, "Approve or reject someone's leave: 'Neha ki leave approve kar do', 'reject Imran's "
      "leave'. Nobody decides their own leave: 'approve my own leave' goes to general_reply.",
      ("list_leave_requests", "propose_leave_decision"),
      ("Find the L… reference with list_leave_requests (awaiting_my_decision).", "If several fit, ask which one.",
       "Call propose_leave_decision.", _ASK)),
    W("onboarding", M, "Onboard a new joiner (HR/admin): 'onboard Rahul as sales exec from 1st Dec', 'new joiner'.",
      ("find_people", "propose_onboarding", "get_onboarding_status"),
      ("Collect name, designation, department, start date and manager (find_people). Ask for a personal email "
       "only if they want a welcome email.", "Status questions: get_onboarding_status.",
       "Call propose_onboarding.", _ASK), required=("propose_onboarding", "get_onboarding_status"),
      roles=frozenset({"admin", "hr_admin"})),
    W("send_message", M, "Send a message, email or announcement to colleagues or outsiders: 'Sales team ko message "
      "bhejo', 'announce the offsite', 'email Arjun', 'mail this to vendor@x.com'.",
      ("find_people", "propose_message"),
      ("Draft a short, clear message yourself (polite Indian-office tone, the language requested).",
       "Colleagues are resolved with find_people; anyone outside the company goes in external_emails (spell back "
       "a spoken address; ask for the address if only a name was given).", "Call propose_message.", _ASK)),
    W("schedule_meeting", M, "Schedule a meeting or interview: 'meeting with Arjun Monday 11', 'set up an "
      "interview with the candidate', 'call with Nimbus tomorrow 4pm'.",
      ("find_people", "propose_meeting"),
      ("Resolve colleagues with find_people; candidates/outsiders go in guest_emails (spell back spoken addresses).",
       "Resolve date and time from today and say them back. Default 30 minutes.",
       "A change of time or attendees means calling propose_meeting again with the new details.",
       "Call propose_meeting.", _ASK)),
    W("read_inbox", M, "Purser inbox messages: 'koi naya message', 'my inbox', 'any messages'.",
      ("read_inbox",), ("Call read_inbox.", "Speak at most three: sender, subject, one-line gist.")),
    W("policy_question", M, "Company policy: 'hotel policy', 'how many WFH days', 'reimbursement rules'.",
      ("lookup_policy",),
      ("Call lookup_policy.", "Answer only from the returned text and cite the section code. If not covered, say "
       "so.")),
]
