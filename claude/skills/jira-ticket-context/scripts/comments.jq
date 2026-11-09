include "adf";

def author:
  .author
  | if type == "object" then (.displayName // .name // "N/A")
    elif type == "string" then .
    else "N/A"
    end;

def render_comment:
  "### \(author) — \(.created // "N/A")\n\n\(.body | body_text)";

# The wrapped form carries Jira's pagination total, which is the reliable way
# to notice a page that was capped below the requested limit.
def missing_count($comments):
  if type == "object" and (.total | type) == "number"
  then ([.total - ($comments | length), 0] | max)
  else 0
  end;

comment_list as $comments
| if $section == "missing" then missing_count($comments)
  elif ($comments | length) == 0 then "No comments."
  else $comments | map(render_comment) | join("\n\n")
  end
