include "adf";

# Input is the slurped stream: issue, its comments, [epic issue, epic comments].
# Everything here is pattern extraction over the fetched text; nothing is inferred.

def url_pattern: "https?://[^\\s)>\\]\"'`<]+";
def key_pattern: "\\b[A-Z][A-Z0-9_]+-[0-9]+\\b";
def path_pattern: "(?<![\\w/.:@-])(?:[\\w.-]+/)*[\\w.-]+\\.(?:go|py|ya?ml|json|md|tf|cue|sh|java|kt|tsx?|js|toml|tpl|xml|gradle|properties|sql|hcl|jsonnet)\\b";

# Standards and acronyms that look like ticket keys (UTF-8, SHA-256, CVE-2024-1).
def non_jira_prefixes:
  ["UTF", "SHA", "ISO", "RFC", "CVE", "MD", "TLS", "SSL", "AES", "RSA", "HTTP", "UUID", "IPV", "UDP", "TCP", "GPT"];

def matches($pattern): [match($pattern; "g").string];

def corpus:
  [(.issue.fields.description | body_text), ((.comments | comment_list)[]? | .body | body_text)]
  | join("\n");

def code_terms:
  [(.issue.fields.description, ((.comments | comment_list)[]? | .body))
   | .. | objects
   | select(.type == "text" and ((.marks // []) | any(.type == "code")))
   | .text];

def attachment_names:
  (.issue.fields.attachment // [])
  | map((.filename // "unnamed") + (if .id then " (id \(.id))" else "" end));

# Parent keys are deliberately not here: only the ticket's parent is shown (as
# the epic's own key), while an epic's parent never appears in the output.
def shown_keys:
  [.issue.key, ((.issue.fields.issuelinks // [])[] | (.outwardIssue.key // .inwardIssue.key))]
  | map(select(. != null));

def tagged($kind; $source): map({kind: $kind, value: ., source: $source});

def matches_urls($text): $text | matches(url_pattern) | map(sub("[.,;:!?]+$"; ""));

def source_items($known):
  corpus as $text
  | .issue.key as $source
  | (matches_urls($text)) as $urls
  | ($urls | tagged("url"; $source))
    + ($text | matches(key_pattern)
       | map(select((split("-")[0]) as $prefix | any(non_jira_prefixes[]; . == $prefix) | not))
       | map(select(. as $key | $known | index($key) | not))
       | tagged("key"; $source))
    + ($text | matches(path_pattern)
       | map(select(. as $path | all($urls[]; contains($path) | not)))
       | tagged("path"; $source))
    + (code_terms | tagged("code"; $source))
    + (attachment_names | tagged("attachment"; $source));

def format_value($kind): if $kind == "code" then "`\(.)`" else . end;

def section($items; $title; $kind):
  [$items[] | select(.kind == $kind)]
  | group_by(.value)
  | map("- \(.[0].value | format_value($kind)) (\(map(.source) | unique | join(", ")))")
  | if length == 0 then empty else "### \($title)\n" + join("\n") end;

. as $documents
| [range(0; length; 2) | {issue: $documents[.], comments: $documents[. + 1]}] as $sources
| ($sources | map(shown_keys) | add) as $known
| ($sources | map(source_items($known)) | add) as $items
| [section($items; "Links"; "url"),
   section($items; "Ticket keys mentioned"; "key"),
   section($items; "File paths"; "path"),
   section($items; "Code terms"; "code"),
   section($items; "Attachments"; "attachment")]
| if length == 0 then "No references found." else join("\n\n") end
