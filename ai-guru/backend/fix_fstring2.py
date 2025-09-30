import re

with open('main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the problematic f-string with a fixed version
# The issue is that f-strings can't contain backslashes in the expression part
# So we need to restructure this

# Find the problematic line and replace it
pattern = r'(\{f"\\*\\*RECENT CONVERSATION CONTEXT:\\\\n\{recent_context\}\\\\n" if recent_context else ""\})\\*\\*CURRENT USER MESSAGE:\\*\\*\\*"'
replacement = 'context_part = f"**RECENT CONVERSATION CONTEXT:**\\n{recent_context}\\n" if recent_context else ""\n{context_part}**CURRENT USER MESSAGE:** """'

content = re.sub(pattern, replacement, content)

with open('main.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed the f-string issue")
