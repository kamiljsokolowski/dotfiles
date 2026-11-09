include "adf";

def not_available: if . == null or . == "" or . == [] then "N/A" else . end;
def display_names: map(.name // .value // tostring);
def person: if . == null then "N/A" else (.displayName // .name // "N/A") end;

# Story Points is requested by name and returned under its instance-specific
# custom-field id; it is the only custom field requested, so the first
# customfield_* key is it. Absent or null renders as N/A.
def story_points:
  [.fields | to_entries[] | select(.key | startswith("customfield_")) | .value] | first;

def link_line:
  if .outwardIssue then "\(.type.outward // .type.name) \(.outwardIssue.key)"
  elif .inwardIssue then "\(.type.inward // .type.name) \(.inwardIssue.key)"
  else empty
  end;

def metadata:
  .fields as $fields
  | [
      "- Key: \(.key)",
      "- Summary: \($fields.summary | not_available)",
      "- Type: \($fields.issuetype.name | not_available)",
      "- Status: \($fields.status.name | not_available)",
      "- Priority: \($fields.priority.name | not_available)",
      "- Assignee: \($fields.assignee | person)",
      "- Reporter: \($fields.reporter | person)",
      "- Labels: \(($fields.labels // []) | join(", ") | not_available)",
      "- Components: \(($fields.components // []) | display_names | join(", ") | not_available)",
      "- Fix Versions: \(($fields.fixVersions // []) | display_names | join(", ") | not_available)",
      "- Story Points: \(story_points | not_available | tostring)",
      "- Linked Issues: \(($fields.issuelinks // []) | map(link_line) | join(", ") | not_available)"
    ]
  | join("\n");

def description:
  (.fields.description | body_text) as $text
  | if ($text | length) == 0 then "No description provided." else $text end;

if $section == "metadata" then metadata
elif $section == "description" then description
elif $section == "parent_key" then (.fields.parent.key // "")
elif $section == "issue_type" then (.fields.issuetype.name // "")
else error("unknown section: \($section)")
end
