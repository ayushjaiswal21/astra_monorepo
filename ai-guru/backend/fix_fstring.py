with open('main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the f-string backslash issue
old_text = '{f"**RECENT CONVERSATION CONTEXT:**\n{recent_context}\n" if recent_context else ""}'
new_text = '{f"**RECENT CONVERSATION CONTEXT:**\\n{recent_context}\\n" if recent_context else ""}'

content = content.replace(old_text, new_text)

with open('main.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed f-string backslashes")
