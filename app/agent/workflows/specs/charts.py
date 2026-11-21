from app.agent.workflows.spec import Workflow as W

M = "charts"
_SPEAK = ("Speak the totals, at most three rows and one insight from the tool result; mention filters that apply. "
          "Never read values off the picture or compute them yourself.")
WORKFLOWS = [
    W("build_chart", M, "A chart, graph or breakdown: 'show me a graph', 'spend by category', 'who owes us', "
      "'monthly revenue', 'allocated vs spent', 'compare with last quarter', 'kaun paisa dena baaki hai'.",
      ("build_chart", "describe_chart_options", "present_view"),
      ("Clear request (metric and grouping known, or one figure): build_chart immediately; default the rest "
       "(current financial year, bar; line for anything over time).",
       "Ambiguous ('show me a graph'): ask_choice(topic='chart'), ONE gap per turn: metric (kind=measure) → time "
       "range (kind=time_range: this_month, this_quarter, this_fy, last_6_months) → grouping (kind=dimension). "
       "Use describe_chart_options for real names. Never more than 3 questions; on LIMIT_REACHED build with defaults.",
       "'Who owes us / kaun paisa dena baaki hai' = receivables_outstanding by customer; 'who do we owe' = "
       "payables_outstanding by vendor.",
       "Quarters follow April-March (Q1 = Apr-Jun). 'vs last quarter/year' = compare=prev_period or yoy.",
       "Two charts together: build each, then present_view.", _SPEAK),
      required=("build_chart", "present_view")),
    W("revise_chart", M, "Change the chart already on screen: 'sirf overdue', 'just Acme', 'make it monthly', "
      "'line chart', 'only Marketing and Travel', 'compare with last quarter' (when a chart is on screen).",
      ("revise_chart", "build_chart", "describe_chart_options"),
      ("Call revise_chart, keeping everything else the same ('sirf overdue' = overdue_only=true; 'monthly' = a "
       "month dimension; 'just Acme' = add_filters).", "If no chart is on screen, build_chart instead.", _SPEAK),
      required=("revise_chart", "build_chart")),
    W("read_chart_value", M, "Read one value from the chart on screen: 'Acme ka amount padho', 'how much is Travel "
      "in that chart'.", ("read_chart_value",),
      ("Call read_chart_value.", "If it returns AMBIGUOUS, read the candidates and ask which one.")),
]
