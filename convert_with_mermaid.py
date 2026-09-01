import re
import subprocess
import os

def process_markdown(input_file, output_pdf):
    print(f"Processing {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find all mermaid blocks
    mermaid_pattern = re.compile(r'```mermaid\n(.*?)\n```', re.DOTALL)
    matches = mermaid_pattern.findall(content)

    new_content = content
    base_name = os.path.splitext(input_file)[0]

    for i, match in enumerate(matches):
        mmd_file = f"{base_name}_diagram_{i}.mmd"
        png_file = f"{base_name}_diagram_{i}.png"
        
        # Write to mmd file
        with open(mmd_file, 'w', encoding='utf-8') as f:
            f.write(match.strip())
        
        print(f"Rendering {mmd_file} to {png_file}...")
        # Run mmdc
        try:
            subprocess.run(["npx", "@mermaid-js/mermaid-cli", "-i", mmd_file, "-o", png_file], check=True, shell=True)
            # Replace in content
            original_block = f"```mermaid\n{match}\n```"
            new_content = new_content.replace(original_block, f"![Diagram]({png_file})")
        except subprocess.CalledProcessError as e:
            print(f"Error rendering {mmd_file}: {e}")

    rendered_md = f"{base_name}_Rendered.md"
    with open(rendered_md, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"Generating PDF for {rendered_md}...")
    try:
        subprocess.run(["markdown-pdf", rendered_md, "-o", output_pdf], check=True, shell=True)
        print(f"Successfully generated {output_pdf}")
    except subprocess.CalledProcessError as e:
        print(f"Error generating PDF: {e}")

if __name__ == "__main__":
    process_markdown("Complete_Project_Report.md", "Complete_Project_Report.pdf")
    process_markdown("Healthcare_AI_Medication_Adherence_IEEE_One_Column_Paper.md", "Healthcare_AI_Medication_Adherence_IEEE_One_Column_Paper.pdf")
