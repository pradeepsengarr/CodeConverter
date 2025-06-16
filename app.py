# Install required packages (run this cell first)
# !pip install gradio requests

import gradio as gr
import requests
import json
import re
import subprocess
import tempfile
import os
from typing import Tuple, Optional
import time

class CodeConverter:
    def __init__(self, api_key: str, api_base_url: str = "https://api.together.xyz/v1"):
        self.api_key = api_key
        self.api_base_url = api_base_url
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
    def detect_language(self, code: str) -> str:
        """Detect programming language from code"""
        code = code.strip()
        
        # Python indicators
        python_indicators = [
            'def ', 'import ', 'from ', 'if __name__', 'print(', 
            'elif ', 'except:', 'with ', 'yield ', 'lambda ',
            'True', 'False', 'None'
        ]
        
        # C++ indicators
        cpp_indicators = [
            '#include', 'using namespace', 'int main(', 'std::', 
            'cout', 'cin', 'endl', 'class ', 'public:', 'private:', 
            'protected:', 'vector<', 'string ', 'int ', 'float ', 
            'double ', 'void ', 'return 0;'
        ]
        
        # Java indicators
        java_indicators = [
            'public class', 'public static void main', 'System.out.println',
            'private ', 'protected ', 'extends ', 'implements ', 'package ',
            'import java.', 'new ', 'String[]'
        ]
        
        # JavaScript indicators
        js_indicators = [
            'function ', 'var ', 'let ', 'const ', 'console.log',
            'document.', 'window.', '=>', 'require(', 'module.exports'
        ]
        
        python_score = sum(1 for indicator in python_indicators if indicator in code)
        cpp_score = sum(1 for indicator in cpp_indicators if indicator in code)
        java_score = sum(1 for indicator in java_indicators if indicator in code)
        js_score = sum(1 for indicator in js_indicators if indicator in code)
        
        # Check for specific patterns
        if re.search(r'^\s*#include\s*<.*>', code, re.MULTILINE):
            cpp_score += 3
        if re.search(r'^\s*def\s+\w+\s*\(', code, re.MULTILINE):
            python_score += 3
        if re.search(r'^\s{4,}', code, re.MULTILINE):  # Python indentation
            python_score += 2
        if re.search(r'public\s+class\s+\w+', code):
            java_score += 3
        if re.search(r'function\s+\w+\s*\(', code):
            js_score += 2
        if code.count('{') > 0 and code.count('}') > 0:
            cpp_score += 1
            java_score += 1
            js_score += 1
            
        scores = {'Python': python_score, 'C++': cpp_score, 'Java': java_score, 'JavaScript': js_score}
        max_lang = max(scores, key=scores.get)
        
        if scores[max_lang] > 0:
            return max_lang
        else:
            return "Unknown"

    def call_llm(self, prompt: str, model: str = "mistralai/Mixtral-8x7B-Instruct-v0.1") -> str:
        """Call Together API for code conversion"""
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": """You are an expert programmer who converts code between different programming languages. 
                    Follow these rules:
                    1. Convert the code to maintain EXACT same functionality
                    2. Use proper syntax and conventions for the target language
                    3. Add necessary imports/headers
                    4. Keep the same logic flow and structure
                    5. Return ONLY the converted code, no explanations or markdown
                    6. Do not add any extra text before or after the code"""
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 3000,
            "temperature": 0.1,
            "top_p": 0.9,
            "repetition_penalty": 1.0
        }
        
        try:
            response = requests.post(
                f"{self.api_base_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code != 200:
                return f"API Error: {response.status_code} - {response.text}"
            
            result = response.json()
            
            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content']
                # Clean up the response
                content = content.strip()
                
                # Remove code block markers if present
                if content.startswith('```'):
                    lines = content.split('\n')
                    # Find the actual code content
                    start_idx = 1
                    end_idx = len(lines)
                    
                    # Look for the end marker
                    for i in range(len(lines)-1, 0, -1):
                        if lines[i].strip() == '```':
                            end_idx = i
                            break
                    
                    content = '\n'.join(lines[start_idx:end_idx])
                
                # Remove any explanatory text at the beginning
                lines = content.split('\n')
                cleaned_lines = []
                code_started = False
                
                for line in lines:
                    # Check if this line looks like code
                    if (line.strip().startswith('#include') or 
                        line.strip().startswith('import ') or
                        line.strip().startswith('from ') or
                        line.strip().startswith('def ') or
                        line.strip().startswith('class ') or
                        line.strip().startswith('public ') or
                        line.strip().startswith('function ') or
                        line.strip().startswith('var ') or
                        line.strip().startswith('let ') or
                        line.strip().startswith('const ') or
                        code_started):
                        code_started = True
                        cleaned_lines.append(line)
                    elif code_started:
                        cleaned_lines.append(line)
                
                return '\n'.join(cleaned_lines) if cleaned_lines else content
            else:
                return "Error: No response generated from API"
                
        except requests.exceptions.RequestException as e:
            return f"Request Error: {str(e)}"
        except Exception as e:
            return f"Error calling LLM API: {str(e)}"

    def convert_code(self, source_code: str, source_lang: str, target_lang: str) -> str:
        """Convert code from source language to target language"""
        if source_lang == target_lang:
            return source_code
            
        # Enhanced prompt for better conversion
        prompt = f"""Convert this {source_lang} code to {target_lang}:

{source_code}

Convert to {target_lang} with:
- Same functionality and logic
- Proper {target_lang} syntax
- Appropriate imports/headers
- Best practices for {target_lang}

Return only the {target_lang} code:"""
        
        return self.call_llm(prompt)

    def compile_cpp(self, cpp_code: str) -> Tuple[bool, str]:
        """Compile C++ code and return success status and output"""
        try:
            # Check if g++ is available
            try:
                subprocess.run(['g++', '--version'], capture_output=True, check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                return False, """❌ C++ compiler not found!
                
For Jupyter Notebook users, install using:
1. Open Anaconda Prompt
2. Run: conda install -c conda-forge gcc_impl_win-64 gxx_impl_win-64
3. Restart Jupyter Notebook

Alternative: Use online C++ compilers like:
- https://www.onlinegdb.com/
- https://replit.com/
- https://ideone.com/"""
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.cpp', delete=False) as f:
                f.write(cpp_code)
                cpp_file = f.name
            
            exe_file = cpp_file.replace('.cpp', '.exe') if os.name == 'nt' else cpp_file.replace('.cpp', '')
            
            # Compile
            compile_cmd = ['g++', '-std=c++17', '-o', exe_file, cpp_file]
            compile_result = subprocess.run(
                compile_cmd, 
                capture_output=True, 
                text=True, 
                timeout=15
            )
            
            if compile_result.returncode == 0:
                # Run the executable
                run_result = subprocess.run(
                    [exe_file], 
                    capture_output=True, 
                    text=True, 
                    timeout=10
                )
                output = f"✅ Compilation successful!\n\n--- Output ---\n{run_result.stdout}"
                if run_result.stderr:
                    output += f"\n--- Warnings ---\n{run_result.stderr}"
                
                # Cleanup
                try:
                    os.unlink(cpp_file)
                    os.unlink(exe_file)
                except:
                    pass
                    
                return True, output
            else:
                # Cleanup
                try:
                    os.unlink(cpp_file)
                except:
                    pass
                return False, f"❌ Compilation failed:\n{compile_result.stderr}"
                
        except subprocess.TimeoutExpired:
            return False, "⏱️ Compilation or execution timed out"
        except Exception as e:
            return False, f"❌ Error during compilation: {str(e)}"

    def run_python(self, python_code: str) -> Tuple[bool, str]:
        """Run Python code and return success status and output"""
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(python_code)
                py_file = f.name
            
            # Run Python code
            run_result = subprocess.run(
                ['python', py_file], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            
            output = f"✅ Execution successful!\n\n--- Output ---\n{run_result.stdout}"
            if run_result.stderr:
                output += f"\n--- Errors/Warnings ---\n{run_result.stderr}"
            
            # Cleanup
            try:
                os.unlink(py_file)
            except:
                pass
                
            return run_result.returncode == 0, output
            
        except subprocess.TimeoutExpired:
            return False, "⏱️ Execution timed out"
        except Exception as e:
            return False, f"❌ Error during execution: {str(e)}"

    def run_java(self, java_code: str) -> Tuple[bool, str]:
        """Compile and run Java code"""
        try:
            # Check if javac is available
            try:
                subprocess.run(['javac', '-version'], capture_output=True, check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                return False, """❌ Java compiler not found!
                
For Jupyter Notebook users, install using:
1. Open Anaconda Prompt
2. Run: conda install openjdk
3. Restart Jupyter Notebook

Alternative: Use online Java compilers like:
- https://www.onlinegdb.com/
- https://replit.com/
- https://jdoodle.com/"""
            
            # Extract class name from code
            class_match = re.search(r'public\s+class\s+(\w+)', java_code)
            if not class_match:
                return False, "❌ Could not find public class declaration"
            
            class_name = class_match.group(1)
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.java', delete=False) as f:
                f.write(java_code)
                java_file = f.name
            
            # Rename file to match class name
            java_dir = os.path.dirname(java_file)
            proper_java_file = os.path.join(java_dir, f"{class_name}.java")
            os.rename(java_file, proper_java_file)
            
            # Compile
            compile_result = subprocess.run(
                ['javac', proper_java_file], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            
            if compile_result.returncode == 0:
                # Run
                run_result = subprocess.run(
                    ['java', '-cp', java_dir, class_name], 
                    capture_output=True, 
                    text=True, 
                    timeout=10
                )
                
                output = f"✅ Compilation and execution successful!\n\n--- Output ---\n{run_result.stdout}"
                if run_result.stderr:
                    output += f"\n--- Errors/Warnings ---\n{run_result.stderr}"
                
                # Cleanup
                try:
                    os.unlink(proper_java_file)
                    os.unlink(os.path.join(java_dir, f"{class_name}.class"))
                except:
                    pass
                    
                return True, output
            else:
                # Cleanup
                try:
                    os.unlink(proper_java_file)
                except:
                    pass
                return False, f"❌ Compilation failed:\n{compile_result.stderr}"
                
        except subprocess.TimeoutExpired:
            return False, "⏱️ Compilation or execution timed out"
        except Exception as e:
            return False, f"❌ Error during compilation/execution: {str(e)}"

    def run_javascript(self, js_code: str) -> Tuple[bool, str]:
        """Run JavaScript code using Node.js"""
        try:
            # Check if node is available
            try:
                subprocess.run(['node', '--version'], capture_output=True, check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                return False, """❌ Node.js not found!
                
For Jupyter Notebook users, install using:
1. Open Anaconda Prompt
2. Run: conda install nodejs
3. Restart Jupyter Notebook

Alternative: Use online JavaScript runners like:
- https://jsfiddle.net/
- https://codepen.io/
- https://replit.com/"""
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
                f.write(js_code)
                js_file = f.name
            
            # Run JavaScript code
            run_result = subprocess.run(
                ['node', js_file], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            
            output = f"✅ Execution successful!\n\n--- Output ---\n{run_result.stdout}"
            if run_result.stderr:
                output += f"\n--- Errors/Warnings ---\n{run_result.stderr}"
            
            # Cleanup
            try:
                os.unlink(js_file)
            except:
                pass
                
            return run_result.returncode == 0, output
            
        except subprocess.TimeoutExpired:
            return False, "⏱️ Execution timed out"
        except Exception as e:
            return False, f"❌ Error during execution: {str(e)}"

def create_interface():
    """Create Gradio interface with standard colors"""
    
    # Main API key
    API_KEY = "97b5edccf9c390dd9293bea7dd4e5ccd6bf016fb3482c2c9700e06f08d99ac3c"
    converter = CodeConverter(API_KEY)
    
    def process_code(source_code: str, target_lang: str, compile_run: bool):
        if not source_code.strip():
            return "Please provide source code", "", ""
        
        # Detect source language
        detected_lang = converter.detect_language(source_code)
        
        if detected_lang == "Unknown":
            return "Could not detect programming language. Please ensure your code is valid.", "", ""
        
        # Convert code
        if detected_lang == target_lang:
            converted_code = source_code
            conversion_info = f"Source language: {detected_lang}\nNo conversion needed - same language selected."
        else:
            conversion_info = f"Detected language: {detected_lang}\nConverting to: {target_lang}\n\nPlease wait..."
            converted_code = converter.convert_code(source_code, detected_lang, target_lang)
            
            if converted_code.startswith("Error") or converted_code.startswith("API Error"):
                conversion_info = f"Detected language: {detected_lang}\nConversion failed: {converted_code}"
                converted_code = ""
            else:
                conversion_info = f"Detected language: {detected_lang}\nConverted to: {target_lang}\n\n✅ Conversion completed successfully!"
        
        # Compile/Run if requested
        execution_output = ""
        if compile_run and converted_code and not converted_code.startswith("Error"):
            if target_lang == "C++":
                success, output = converter.compile_cpp(converted_code)
                execution_output = output
            elif target_lang == "Python":
                success, output = converter.run_python(converted_code)
                execution_output = output
            elif target_lang == "Java":
                success, output = converter.run_java(converted_code)
                execution_output = output
            elif target_lang == "JavaScript":
                success, output = converter.run_javascript(converted_code)
                execution_output = output
        
        return conversion_info, converted_code, execution_output

    # Create interface with standard blue theme
    with gr.Blocks(
        theme=gr.themes.Default(
            primary_hue="blue",
            secondary_hue="gray",
            neutral_hue="slate"
        ),
        title="Code Converter",
        css="""
        .gradio-container {
            max-width: 100% !important;
        }
        .header-box {
            background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            margin-bottom: 20px;
        }
        .example-box {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 15px;
            margin-top: 20px;
        }
        """
    ) as interface:
        
        gr.HTML("""
        <div class="header-box">
            <h1 style="margin-bottom: 10px; font-size: 2rem;">Code Converter & Compiler</h1>
            <p style="opacity: 0.9; font-size: 1.1rem;">Convert between Python, C++, Java, and JavaScript</p>
        </div>
        """)
        
        # Input section
        with gr.Row():
            with gr.Column(scale=3):
                source_code_input = gr.Code(
                    label="Source Code",
                    lines=15,
                    language="python",
                    value="# Example Python code\ndef fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)\n\nfor i in range(10):\n    print(f'F({i}) = {fibonacci(i)}')"
                )
            
            with gr.Column(scale=1):
                target_lang_dropdown = gr.Dropdown(
                    choices=["Python", "C++", "Java", "JavaScript"],
                    label="Convert To",
                    value="C++",
                )
                
                compile_run_checkbox = gr.Checkbox(
                    label="Compile/Run after conversion",
                    value=True,
                )
                
                convert_button = gr.Button(
                    "Convert Code", 
                    variant="primary",
                    size="lg"
                )
        
        # Output section
        conversion_info = gr.Textbox(
            label="Conversion Info",
            lines=4,
            interactive=False
        )
        
        converted_code_output = gr.Code(
            label="Converted Code",
            lines=15
        )
        
        execution_output = gr.Textbox(
            label="Compilation/Execution Output",
            lines=8,
            interactive=False
        )
        
        # Event handlers
        convert_button.click(
            fn=process_code,
            inputs=[source_code_input, target_lang_dropdown, compile_run_checkbox],
            outputs=[conversion_info, converted_code_output, execution_output]
        )
        
        # Update syntax highlighting
        def update_syntax_highlighting(target_lang):
            lang_map = {
                "Python": "python",
                "C++": "cpp", 
                "Java": "java",
                "JavaScript": "javascript"
            }
            return gr.Code.update(language=lang_map.get(target_lang, "text"))
        
        target_lang_dropdown.change(
            fn=update_syntax_highlighting,
            inputs=[target_lang_dropdown],
            outputs=[converted_code_output]
        )
        
        # Examples section
        gr.HTML("""
        <div class="example-box">
            <h3>Example Code Snippets:</h3>
            <details style="margin: 10px 0;">
                <summary style="cursor: pointer; font-weight: bold;">Python - Factorial Function</summary>
                <pre style="background: #f1f5f9; padding: 10px; border-radius: 5px; margin: 10px 0;">def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)

print(f"5! = {factorial(5)}")
print(f"10! = {factorial(10)}")</pre>
            </details>
            <details style="margin: 10px 0;">
                <summary style="cursor: pointer; font-weight: bold;">C++ - Array Sum</summary>
                <pre style="background: #f1f5f9; padding: 10px; border-radius: 5px; margin: 10px 0;">#include &lt;iostream&gt;
using namespace std;

int main() {
    int arr[] = {1, 2, 3, 4, 5};
    int sum = 0;
    
    for(int i = 0; i < 5; i++) {
        sum += arr[i];
    }
    
    cout &lt;&lt; "Sum: " &lt;&lt; sum &lt;&lt; endl;
    return 0;
}</pre>
            </details>
            <details style="margin: 10px 0;">
                <summary style="cursor: pointer; font-weight: bold;">Java - Simple Class</summary>
                <pre style="background: #f1f5f9; padding: 10px; border-radius: 5px; margin: 10px 0;">public class Calculator {
    public static int add(int a, int b) {
        return a + b;
    }
    
    public static void main(String[] args) {
        int result = add(5, 3);
        System.out.println("Result: " + result);
    }
}</pre>
            </details>
        </div>
        """)

    return interface

# Launch the interface
print("🚀 Starting Code Converter...")
print("✅ API Key configured and ready")
print("🌐 Interface will launch in your browser")

# Create and launch interface
app = create_interface()

# Launch with automatic port selection
app.launch(
    share=False,
    debug=False,
    inbrowser=True
)
