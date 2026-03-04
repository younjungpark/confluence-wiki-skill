import sys
import re
import os

def calculate_list_level(indent):
    return (indent // 2) + 1

def find_parent_bullet_level(lines, current_index, current_indent):
    j = current_index - 1
    while j >= 0:
        prev_line = lines[j]
        if prev_line.strip() == '':
            j -= 1
            continue

        if prev_line.strip().startswith('```'):
            break

        numbered_match = re.match(r'^(\s*)(\d+)\.\s+(.+)$', prev_line)
        bullet_match = re.match(r'^(\s*)([-*])\s+(.+)$', prev_line)
        if numbered_match or bullet_match:
            match_obj = numbered_match if numbered_match else bullet_match
            prev_indent = len(match_obj.group(1))
            if prev_indent >= current_indent:
                j -= 1
                continue

            if bullet_match:
                return calculate_list_level(prev_indent)
            return 0

        break

    return 0

def remove_emojis(text):
    # 1. Astral Plane (Most emojis like 🐳, 📝, 💡)
    text = re.sub(r'[\U00010000-\U0010ffff]', '', text)
    # 2. Key lower plane emoji ranges
    # ⏳ (\u23F3), ℹ️ (\u2139), ⚠️ (\u26A0)
    text = re.sub(r'[\u2600-\u26FF\u2700-\u2704\u2706-\u274B\u274D-\u27BF\u2300-\u23FF]', '', text)
    return text

def process_inline_formatting(text):
    if not text:
        return text
        
    # 1. Bold (**text** -> * text * )
    text = re.sub(r'\*\*(.*?)\*\*', r' *\1* ', text)
    
    # 2. Inline Code (`text` -> text with escapes)
    def smart_inline_code(match):
        content = match.group(1)
        # Escape significant Wiki characters
        processed = content.replace('{', r'\{').replace('}', r'\}')
        processed = processed.replace('[', r'\[').replace(']', r'\]')
        processed = processed.replace('|', r'\|')
        processed = processed.replace('*', r'\*')
        return processed
        
    text = re.sub(r'`([^`]+)`', smart_inline_code, text)
    
    # 3. Links ([Text](URL) -> [Text|URL])
    text = re.sub(r'\[([^\]]+)\]\(((?:https?://|/|#|mailto:)[^)]+)\)', r'[\1|\2]', text)
    
    # 4. Escape special chars (if not already handled)
    text = re.sub(r'(?<!\\)(?<!\{)\{(?!\{)', r'\{', text)
    text = re.sub(r'(?<!\\)(?<!\})\}(?!\})', r'\}', text)
    text = re.sub(r'(?<!\\)\[(?!(?:https?://|[^\]]+\|))', r'\[', text)
    
    return text

def is_markdown_list_line(text):
    return re.match(r'^\s*(\d+\.\s+|[-*]\s+).+$', text) is not None

def is_confluence_list_line(text):
    return re.match(r'^([#*]+|\d+\))\s+.+$', text) is not None

def convert_to_confluence(content):
    lines = content.split('\n')
    output = []
    in_code_block = False
    in_numbered_list = False
    numbered_list_indent = None
    
    # Supported languages
    SUPPORTED_LANGUAGES = {
        'actionscript3', 'bash', 'csharp', 'coldfusion', 'cpp', 'css', 
        'delphi', 'diff', 'erlang', 'groovy', 'java', 'javafx', 
        'javascript', 'perl', 'php', 'powershell', 'python', 'ruby', 
        'scala', 'sql', 'vb', 'html/xml'
    }

    i = 0
    while i < len(lines):
        line = lines[i]
        
        # 1. Code Block
        if line.strip().startswith('```'):
            if in_code_block:
                 if hasattr(convert_to_confluence, 'current_lang') and convert_to_confluence.current_lang == 'mermaid':
                     output.append('```')
                 output.append('{code}')
                 in_code_block = False
                 convert_to_confluence.current_lang = None
            else:
                lang = line.strip()[3:].strip()
                lang_lower = lang.lower()
                if lang_lower in ['xml', 'html']: lang_lower = 'html/xml'
                
                if lang_lower == 'mermaid':
                    output.append('{code:collapse=true}')
                    output.append('```mermaid')
                    convert_to_confluence.current_lang = 'mermaid'
                elif lang_lower in SUPPORTED_LANGUAGES:
                    output.append(f'{{code:language={lang_lower}}}')
                    convert_to_confluence.current_lang = lang_lower
                else:
                    output.append('{code}')
                    convert_to_confluence.current_lang = None
                in_code_block = True
            i += 1
            continue
        
        if in_code_block:
            output.append(line)
            i += 1
            continue

        # 2. Info/Warning Boxes
        if line.strip().startswith('>'):
            box_type = None
            pattern = None
            
            if re.search(r'>\s*\*\*(?:\[\s*)?.*(?:Info|정보|ℹ️)(?:\s*\])?.*\*\*', line, re.IGNORECASE):
                box_type = '{info:title=Info}'
                pattern = r'> \*\*.*(?:Info|정보|ℹ️).*\*\*[:\s]*(.*)'
            elif re.search(r'>\s*\*\*(?:\[\s*)?.*(?:Warning|경고|주의|⚠️)(?:\s*\])?.*\*\*', line, re.IGNORECASE):
                box_type = '{warning:title=Warning}'
                pattern = r'> \*\*.*(?:Warning|경고|주의|⚠️).*\*\*[:\s]*(.*)'
            elif re.search(r'>\s*\*\*(?:\[\s*)?.*(?:Important|중요|❗)(?:\s*\])?.*\*\*', line, re.IGNORECASE):
                box_type = '{warning:title=중요}'
                pattern = r'> \*\*.*(?:Important|중요|❗).*\*\*[:\s]*(.*)'
            elif re.search(r'>\s*\*\*(?:\[\s*)?.*(?:Note|참고|📝)(?:\s*\])?.*\*\*', line, re.IGNORECASE):
                box_type = '{note:title=참고}'
                pattern = r'> \*\*.*(?:Note|참고|📝).*\*\*[:\s]*(.*)'
            
            github_alert_match = re.match(r'>\s*\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]', line.strip())
            if github_alert_match:
                 alert_type = github_alert_match.group(1)
                 if alert_type == 'NOTE': box_type = '{note}'
                 elif alert_type == 'TIP': box_type = '{tip}'
                 elif alert_type == 'IMPORTANT': box_type = '{warning:title=중요}'
                 elif alert_type == 'WARNING': box_type = '{warning}'
                 elif alert_type == 'CAUTION': box_type = '{warning:title=주의}'
                 pattern = None

            if box_type:
                output.append(box_type)
                if pattern:
                    match = re.search(pattern, line)
                    if match:
                        content = match.group(1).strip()
                        if content:
                            content = remove_emojis(content)
                            content = process_inline_formatting(content)
                            output.append(content)
                
                i += 1
                container_in_code = False
                box_in_numbered_list = False
                box_numbered_indent = None
                while i < len(lines) and lines[i].strip().startswith('>'):
                    raw_line = lines[i].strip()
                    content_line = raw_line[2:] if raw_line.startswith('> ') else raw_line[1:]
                    
                    if content_line.strip().startswith('```'):
                        output.append('{code}')
                        container_in_code = not container_in_code
                    else:
                        if content_line.strip():
                            content_line = remove_emojis(content_line)
                            if not container_in_code:
                                # Lists inside boxes must also be converted to Confluence list syntax.
                                numbered_match = re.match(r'^(\s*)(\d+)\.\s+(.+)$', content_line)
                                if numbered_match:
                                    indent = len(numbered_match.group(1))
                                    hash_count = calculate_list_level(indent)
                                    text = process_inline_formatting(numbered_match.group(3))
                                    output.append(f"{'#' * hash_count} {text}")
                                    box_in_numbered_list = True
                                    box_numbered_indent = indent
                                    i += 1
                                    continue

                                list_match = re.match(r'^(\s*)([-*])\s+(.+)$', content_line)
                                if list_match:
                                    indent = len(list_match.group(1))
                                    text = process_inline_formatting(list_match.group(3))
                                    if box_in_numbered_list and box_numbered_indent is not None and indent >= box_numbered_indent:
                                        relative_indent = indent - box_numbered_indent
                                        star_count = max(1, relative_indent // 4)
                                        output.append(f"#{'*' * star_count} {text}")
                                    else:
                                        star_count = calculate_list_level(indent)
                                        if indent == 0:
                                            box_in_numbered_list = False
                                            box_numbered_indent = None
                                        output.append(f"{'*' * star_count} {text}")
                                    i += 1
                                    continue

                                box_in_numbered_list = False
                                box_numbered_indent = None
                                content_line = process_inline_formatting(content_line)
                            output.append(content_line)
                        else:
                            box_in_numbered_list = False
                            box_numbered_indent = None
                            output.append('')
                    i += 1
                
                if container_in_code: output.append('{code}')
                match_tag = re.match(r'\{([a-zA-Z]+)', box_type)
                if match_tag: output.append(f'{{{match_tag.group(1)}}}')
                continue

        # 3. Headings
        if line.strip().startswith('#'):
            match = re.match(r'^(\s*)(#+)\s+(.+)$', line)
            if match:
                level = len(match.group(2))
                text = match.group(3)
                text = re.sub(r'`([^`]+)`', r'\1', text)
                text = text.replace('**', '').replace('[', '\[').replace(']', '\]')
                output.append(f'h{level}. {text}')
                i += 1
                continue

        # Blank line handling:
        # Confluence resets numbered lists when blank lines exist between list items.
        if line.strip() == '':
            next_index = i + 1
            while next_index < len(lines) and lines[next_index].strip() == '':
                next_index += 1

            prev_non_empty = ''
            j = len(output) - 1
            while j >= 0:
                if output[j].strip() != '':
                    prev_non_empty = output[j].strip()
                    break
                j -= 1

            next_line = lines[next_index] if next_index < len(lines) else ''
            if prev_non_empty and is_confluence_list_line(prev_non_empty) and is_markdown_list_line(next_line):
                i += 1
                continue

            in_numbered_list = False
            numbered_list_indent = None
            output.append('')
            i += 1
            continue

        # 4. Tables
        if line.strip().startswith('|'):
            if output and output[-1].strip() != '' and not output[-1].strip().startswith('|'):
                output.append('')

            if i + 1 < len(lines) and re.match(r'^\s*\|[-:| ]+\|\s*$', lines[i+1]):
                cells = line.strip().split('|')[1:-1]
                # Apply inline formatting to header cells
                converted = [process_inline_formatting(c.strip()) for c in cells]
                output.append('|| ' + ' || '.join(converted) + ' ||')
                i += 2
                continue
            else:
                cells = line.strip().split('|')[1:-1]
                # Apply inline formatting and <br> conversion to normal cells
                converted = [process_inline_formatting(c.strip().replace('<br>', ' \\\\ ').replace('<br/>', ' \\\\ ')) for c in cells]
                output.append('| ' + ' | '.join(converted) + ' |')
                i += 1
                continue

        # 5. Lists (Outer)
        numbered_match = re.match(r'^(\s*)(\d+)\.\s+(.+)$', line)
        if numbered_match:
            indent = len(numbered_match.group(1))
            text = process_inline_formatting(numbered_match.group(3))

            # Confluence can reset numbered lists when a list item is followed by a fenced code block.
            # In that case, keep the source number as plain text to preserve visible numbering.
            next_index = i + 1
            while next_index < len(lines) and lines[next_index].strip() == '':
                next_index += 1
            has_following_code_block = next_index < len(lines) and lines[next_index].strip().startswith('```')

            if has_following_code_block:
                output.append(f"{numbered_match.group(2)}) {text}")
                in_numbered_list = False
                numbered_list_indent = None
            else:
                parent_bullet_level = find_parent_bullet_level(lines, i, indent)
                if parent_bullet_level > 0:
                    output.append(f"{'*' * parent_bullet_level}# {text}")
                else:
                    hash_count = calculate_list_level(indent)
                    output.append(f"{'#' * hash_count} {text}")
                in_numbered_list = True
                numbered_list_indent = indent
            i += 1
            continue
        
        list_match = re.match(r'^(\s*)([-*])\s+(.+)$', line)
        if list_match:
            if line.strip() == '---': 
                i += 1
                continue
            indent = len(list_match.group(1))
            text = process_inline_formatting(list_match.group(3))
            if in_numbered_list and numbered_list_indent is not None and indent >= numbered_list_indent:
                relative_indent = indent - numbered_list_indent
                star_count = max(1, relative_indent // 4)
                output.append(f"#{'*' * star_count} {text}")
            else:
                star_count = calculate_list_level(indent)
                if indent == 0:
                    in_numbered_list = False
                    numbered_list_indent = None
                output.append(f"{'*' * star_count} {text}")
            i += 1
            continue

        if not numbered_match and not list_match:
            in_numbered_list = False
            numbered_list_indent = None

        if line.strip() == '---':
            i += 1
            continue
            
        line = remove_emojis(line)
        output.append(process_inline_formatting(line))
        i += 1

    return '\n'.join(output)

def convert_file(input_file, output_file):
    if not os.path.exists(input_file): return
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    converted = convert_to_confluence(content)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(converted)
    print(f"Successfully converted and saved to: {output_file}")

if __name__ == "__main__":
    if sys.stdout.encoding != 'utf-8': sys.stdout.reconfigure(encoding='utf-8')
    input_file = sys.argv[1]
    file_no_ext = os.path.splitext(input_file)[0]
    output_file = sys.argv[2] if len(sys.argv) >= 3 else f"{file_no_ext}.wiki"
    convert_file(input_file, output_file)
