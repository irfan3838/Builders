from app.agent.workflows.spec import Workflow as W

M = "work"
WORKFLOWS = [
    W("tasks", M, "My tasks: 'my tasks', 'what do I have to do', 'add a task', 'remind me to …', 'T12 done', 'cab "
      "receipts wala done ho gaya'. NOT for revenue reminders about a client (reminders).",
      ("list_tasks", "add_task", "complete_task"),
      ("List: list_tasks. Add: add_task, resolving the date from today and saying it back. Done: complete_task "
       "(find the T… with list_tasks if the user named it in words).", "These are saved directly, no confirmation.")),
    W("assign_task", M, "Give a task to someone (managers): 'give Rahul the deck review by Friday', 'assign this "
      "to Neha'.", ("find_people", "propose_assign_task"),
      ("find_people for the person.", "Call propose_assign_task with the due date resolved from today.",
       "Read 'say'; ask; stop.")),
    W("raise_ticket", M, "A helpdesk problem or request: 'laptop not working', 'need access to …', 'AC broken', "
      "'raise a ticket'.", ("propose_ticket",),
      ("Pick the category (it, admin, facilities, hr, finance) and a clear title.", "Call propose_ticket.",
       "Read 'say'; ask; stop.")),
    W("ticket_status", M, "Helpdesk ticket status or update: 'status of my ticket', 'resolve HD3', 'my laptop "
      "ticket'.", ("list_tickets", "propose_ticket_update"),
      ("Status: list_tickets. Admin/HR resolving or updating: propose_ticket_update, then read 'say', ask, stop.")),
]
