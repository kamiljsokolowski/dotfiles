def adf_text:
  if type == "string" then .
  elif type == "array" then map(adf_text) | join("")
  elif type == "object" then
    (.type // "") as $node_type
    | if $node_type == "text" then
        .text + ((.marks // []) | map(select(.type == "link") | " (" + .attrs.href + ")") | join(""))
      elif $node_type == "hardBreak" then "\n"
      elif $node_type == "mention" then (.attrs.text // "")
      elif $node_type == "emoji" then (.attrs.text // .attrs.shortName // "")
      elif ($node_type == "inlineCard" or $node_type == "blockCard") then (.attrs.url // "")
      elif ($node_type == "paragraph" or $node_type == "heading") then ((.content // []) | adf_text) + "\n"
      elif $node_type == "listItem" then "- " + ((.content // []) | adf_text)
      elif $node_type == "codeBlock" then "```\n" + ((.content // []) | adf_text) + "\n```\n"
      else ((.content // []) | adf_text)
      end
  else ""
  end;

# Accepts a bare array or an object wrapping it, since acli-pii's JSON shape
# for comment list is not documented.
def comment_list:
  if type == "array" then .
  elif type == "object" then (.comments // [])
  else []
  end;

def body_text:
  (if type == "object" then adf_text elif type == "string" then . else "" end)
  | rtrimstr("\n")
  | gsub("\n{3,}"; "\n\n");
