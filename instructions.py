SYSTEM_INSTRUCTION = """
You are an AI-powered content transformation engine.

Your task is to transform the provided source content into the communication
artefact requested by the user.

Follow these rules strictly:

1. Preserve the factual meaning of the source content.

2. Do not invent facts, names, dates, statistics, events, quotations,
   organisations, locations, technical details, or recommendations that
   are not supported by the source.

3. Adapt the content according to the following requirements:
   - Target audience
   - Communication objective
   - Tone
   - Language
   - Level of detail
   - Content style
   - Output type
   - Output format

4. Make the output appropriate for the specified target audience.

5. Preserve important information from the source while removing
   irrelevant information when the requested detail level is concise.

6. If the source does not contain enough information to support a claim,
   do not fabricate the missing information.

7. Keep the generated content clear, coherent and professionally structured.

8. Respect the requested level of detail:
   - Concise: only the most important information
   - Moderate: important information with necessary context
   - Detailed: comprehensive coverage of relevant information
   - Comprehensive: exhaustive coverage of all relevant information

9. Follow the structure normally expected for the requested output type.

10. Return only the requested transformed content.
    Do not explain the transformation process.

11. Treat all provided transformation parameters as explicit user-selected
requirements. When the output explicitly refers to any selected parameter,
use the selected value or its direct wording. Do not replace it with a
semantic equivalent, broader category, synonym, or inferred audience.
Do not force the parameter value into places where it is not naturally needed.

12. Follow the OUTPUT FORMAT RULES given below exactly. These rules control
how the response must be structured so it can be parsed programmatically.
Do not deviate from the required markers, delimiters or limits even if the
source content is long or short.
"""


# Keyed by output_format exactly as sent by the frontend: PDF, DOCX, PPTX, PNG.
# Only formats that need a strict, parseable structure are listed here.
FORMAT_RULES = {
    "PPTX": """
STRUCTURE RULES (required for this file format):
- Output must contain between 5 and 12 slides.
- Use EXACTLY this format for every slide, with no extra text before or after:

[SLIDE: <slide title, max 8 words>]
- <bullet point 1>
- <bullet point 2>
- <bullet point 3 (optional)>
- <bullet point 4 (optional)>
[NOTES: <speaker notes for this slide, 1-3 sentences>]

- Repeat the block above for every slide.
- Do not use markdown headings, numbering, or any symbol other than "-"
  for bullets.
- Do not merge multiple slides into one block.
- The first slide must be a title slide with the presentation title as the
  slide title and the bullets containing subtitle/context only.
""",
}


# Keyed by output_type exactly as sent by the frontend.
TYPE_RULES = {
    "Executive Summary": """
STRUCTURE RULES (Executive Summary):
- Maximum 300 words.
- 3-5 short paragraphs or bullet points, no sub-headings.
- No introductory phrases like "This document summarises...".
""",

    "Advisory": """
STRUCTURE RULES (Advisory):
- Start with "# " followed by the advisory title.
- Include these sections in order, each prefixed with "## ":
  Summary, Background, Key Points, Recommended Actions, Contact/Reference
  (only if source supports it).
- Use "- " prefix for bullet lists inside Key Points and Recommended Actions.
""",

    "Press Release": """
STRUCTURE RULES (Press Release):
- Start with "# " followed by a newsworthy headline.
- First paragraph must cover who/what/when/where/why.
- Include a short quote-style paragraph only if the source supports one.
- End with a brief "About" line only if the source provides organisational
  context; otherwise omit it.
""",

    "Report": """
STRUCTURE RULES (Report):
- Start with "# " followed by the report title.
- Include sections prefixed with "## ": Overview, Findings, Analysis,
  Conclusion (adapt section names only if the source clearly demands it).
""",

    "Briefing Note": """
STRUCTURE RULES (Briefing Note):
- Start with "# " followed by the briefing subject.
- Include "## Situation", "## Key Points", "## Recommendation" sections.
- Keep each section tight; briefing notes are meant to be read in minutes.
""",

    "Study Notes": """
STRUCTURE RULES (Study Notes):
- Use "## " for each topic/section heading.
- Use "- " bullet points for key facts under each heading.
- Prioritise clarity and memorability over prose style.
""",

    "Policy Summary": """
STRUCTURE RULES (Policy Summary):
- Start with "# " followed by the policy name.
- Include "## Purpose", "## Key Provisions", "## Impact" sections.
- Use "- " bullets for Key Provisions.
""",

    "Meeting Minutes": """
STRUCTURE RULES (Meeting Minutes):
- Include "## Attendees", "## Discussion Points", "## Action Items"
  sections (only include Attendees if the source names participants).
- Use "- " bullets under each section.
""",

    "Newsletter": """
STRUCTURE RULES (Newsletter):
- Start with "# " followed by a newsletter headline.
- Use "## " for distinct story/section headings if multiple topics exist.
- Keep tone engaging and scannable.
""",

    "Article": """
STRUCTURE RULES (Article):
- Start with "# " followed by a headline.
- Use flowing prose paragraphs; use "## " sub-headings only for longer,
  multi-section articles.
""",

    "Public Notice": """
STRUCTURE RULES (Public Notice):
- Start with "# NOTICE" or a similarly clear notice header.
- State the subject, effective details, and any required action plainly
  in short paragraphs.
""",

    "FAQ": """
STRUCTURE RULES (FAQ):
- Use this format for every entry:

**Q: <question>**
<answer>

- Repeat for every question. Only include questions the source content
  can genuinely answer.
""",

    "Email": """
STRUCTURE RULES (Email):
- Start with "Subject: <subject line>" on the first line.
- Leave a blank line, then write the email body in plain paragraphs.
- Do not use markdown headings.
""",

    "Speech": """
STRUCTURE RULES (Speech):
- Write in flowing spoken-language paragraphs meant to be read aloud.
- No markdown headings, bullets, or symbols.
- Include a brief opening address and closing line appropriate to the
  audience.
""",

    "Infographic Content": """
STRUCTURE RULES (Infographic Content):
- Output must contain between 4 and 8 content blocks.
- Use EXACTLY this format for every block:

[BLOCK: <short label, max 5 words>]
<one key statistic, fact or statement, max 20 words>

- Repeat for every block. Do not add explanations outside this format.
""",
}


# Keyed by content_style exactly as sent by the frontend, for the
# social-media-platform styles that carry hard external constraints.
STYLE_RULES = {
    "Twitter / X Post": """
PLATFORM RULES (Twitter/X):
- If content fits in 280 characters, output a single tweet only.
- If it does not fit, output a thread using EXACTLY this format:

[TWEET 1]
<text, max 280 characters including numbering like "1/">
[TWEET 2]
<text, max 280 characters>

- Repeat for each tweet. Maximum 8 tweets in a thread.
- No markdown, no headings. Hashtags only in the final tweet (max 3).
""",

    "Instagram Post": """
PLATFORM RULES (Instagram Post):
- Start with a short attention-grabbing first line (max 125 characters).
- Caption body: max 2200 characters total including hashtags.
- Conversational tone, short line breaks allowed.
- End with a block of 5-15 relevant hashtags, prefixed with "#".
""",

    "Instagram Caption": """
PLATFORM RULES (Instagram Caption):
- Maximum 2200 characters including hashtags.
- Short, punchy sentences; minimal formatting.
- End with 3-10 relevant hashtags.
""",

    "LinkedIn Post": """
PLATFORM RULES (LinkedIn Post):
- Maximum 1300 characters including hashtags.
- Professional tone, no more than 2 emojis total.
- Short paragraphs (1-3 lines each), plain text, no markdown symbols.
- End with 3-5 relevant hashtags on a new line.
- Do not include a title or heading line.
""",

    "Facebook Post": """
PLATFORM RULES (Facebook Post):
- Maximum 500 characters for best engagement, hard cap 2000 characters.
- Conversational tone, short paragraphs.
- Hashtags optional, maximum 2 if used.
""",

    "YouTube Description": """
PLATFORM RULES (YouTube Description):
- First 2 lines (max 150 characters total) must summarise the video, as
  this is what shows before "more".
- Follow with a longer description, then relevant links/credits only if
  the source provides them.
- End with 3-8 relevant hashtags.
""",

    "YouTube Community Post": """
PLATFORM RULES (YouTube Community Post):
- Maximum 1500 characters.
- Casual, direct tone, written like an update to subscribers.
""",

    "Threads Post": """
PLATFORM RULES (Threads Post):
- Maximum 500 characters per post.
- If content needs more than one post, use EXACTLY this format:

[POST 1]
<text, max 500 characters>
[POST 2]
<text, max 500 characters>

- Maximum 6 posts.
""",

    "TikTok Caption": """
PLATFORM RULES (TikTok Caption):
- Maximum 150 characters.
- Short, punchy, trend-aware tone.
- End with 3-5 relevant hashtags.
""",

    "TikTok Script": """
PLATFORM RULES (TikTok Script):
- Use EXACTLY this format:

[HOOK: <first 3 seconds, max 15 words>]
[BODY: <main content, spoken-style, max 45 seconds of speech>]
[CTA: <closing call-to-action, max 10 words>]
""",
}


def build_transformation_prompt(
    source_content,
    audience,
    objective,
    tone,
    language,
    detail_level,
    content_style,
    output_type,
    output_format,
    additional_instructions
):
    rule_blocks = [
        FORMAT_RULES.get(output_format, ""),
        TYPE_RULES.get(output_type, ""),
        STYLE_RULES.get(content_style, ""),
    ]

    combined_rules = "\n".join(block for block in rule_blocks if block.strip())

    prompt = f"""
Transform the following source content according to the specified
transformation requirements.

================ SOURCE CONTENT ================

{source_content}

================ REQUIREMENTS ================

Target Audience:
{audience}

Communication Objective:
{objective}

Tone:
{tone}

Language:
{language}

Level of Detail:
{detail_level}

Content Style:
{content_style}

Output Type:
{output_type}

Output Format:
{output_format}
================ ADDITIONAL INSTRUCTIONS ===============
{additional_instructions if additional_instructions.strip() else "No additional instructions provided."}
{combined_rules}
================ TASK ================
Generate the requested {output_type} using the source content.
The output must:
- be suitable for the specified audience
- fulfil the specified communication objective
- follow the requested tone and style
- respect the requested level of detail
- preserve important factual information
- avoid unsupported or fabricated information
- follow the OUTPUT FORMAT RULES exactly when given above
- follow the additional instructions when provided
- treat additional instructions as output constraints or requirements
Return only the final transformed content.
"""
    return prompt



# SYSTEM_INSTRUCTION = """
# You are an AI-powered content transformation engine.

# Your task is to transform the provided source content into the communication
# artefact requested by the user.

# Follow these rules strictly:

# 1. Preserve the factual meaning of the source content.

# 2. Do not invent facts, names, dates, statistics, events, quotations,
#    organisations, locations, technical details, or recommendations that
#    are not supported by the source.

# 3. Adapt the content according to the following requirements:
#    - Target audience
#    - Communication objective
#    - Tone
#    - Language
#    - Level of detail
#    - Content style
#    - Output type

# 4. Make the output appropriate for the specified target audience.

# 5. Preserve important information from the source while removing
#    irrelevant information when the requested detail level is concise.

# 6. If the source does not contain enough information to support a claim,
#    do not fabricate the missing information.

# 7. Keep the generated content clear, coherent and professionally structured.

# 8. Respect the requested level of detail:
#    - Concise: only the most important information
#    - Moderate: important information with necessary context
#    - Detailed: comprehensive coverage of relevant information

# 9. Follow the structure normally expected for the requested output type.

# 10. Return only the requested transformed content.
#     Do not explain the transformation process.

# 11. Treat all provided transformation parameters as explicit user-selected
# requirements. When the output explicitly refers to any selected parameter,
# use the selected value or its direct wording. Do not replace it with a
# semantic equivalent, broader category, synonym, or inferred audience.
# Do not force the parameter value into places where it is not naturally needed.

# 12. Follow the OUTPUT FORMAT RULES given below exactly. These rules control
# how the response must be structured so it can be parsed programmatically.
# Do not deviate from the required markers, delimiters or limits even if the
# source content is long or short.

# 13. When the selected language is Hindi:
#     - Write in natural, modern Hindi commonly used in everyday professional communication.
#     - Use correct Devanagari spelling and vowel matras.
#     - Use half-letters (halant/virama) only where they are naturally required in standard Hindi spelling.
#     - Avoid unnecessary Sanskritized, overly formal, archaic, or literary vocabulary.
#     - Prefer simple and familiar Hindi words used in modern communication.
#     - Do not transliterate Hindi into English unless the term is commonly used in English in the given context.
# """


# OUTPUT_TYPE_RULES = {
#     "ppt": """
# OUTPUT FORMAT RULES (Presentation):
# - Output must contain between 5 and 12 slides.
# - Use EXACTLY this format for every slide, with no extra text before or after:

# [SLIDE: <slide title, max 8 words>]
# - <bullet point 1>
# - <bullet point 2>
# - <bullet point 3 (optional)>
# - <bullet point 4 (optional)>
# [NOTES: <speaker notes for this slide, 1-3 sentences>]

# - Repeat the block above for every slide.
# - Do not use markdown headings, numbering, or any symbol other than "-"
#   for bullets.
# - Do not merge multiple slides into one block.
# - The first slide must be a title slide with the presentation title as the
#   slide title and the bullets containing subtitle/context only.
# - Do not include a "Thank you" slide unless the source content explicitly
#   requires one.
# """,

#     "docx": """
# OUTPUT FORMAT RULES (Word Document):
# - Start with a single line title, prefixed with "# ".
# - Use "## " prefix for section headings.
# - Use plain paragraphs for body text (no markdown bold/italics).
# - Use "- " prefix for bullet lists where appropriate.
# - Do not use tables unless the source content is explicitly tabular.
# """,

#     "advisory": """
# OUTPUT FORMAT RULES (Advisory Document):
# - Start with "# " followed by the advisory title.
# - Include these sections in order, each prefixed with "## ":
#   Summary, Background, Key Points, Recommended Actions, Contact/Reference
#   (only if source supports it).
# - Use "- " prefix for bullet lists inside Key Points and Recommended Actions.
# """,

#     "executive_summary": """
# OUTPUT FORMAT RULES (Executive Summary):
# - Maximum 300 words.
# - Start with "# Executive Summary".
# - Use 3-5 short paragraphs or bullet points, no sub-headings.
# - No introductory phrases like "This document summarises...".
# """,

#     "linkedin": """
# OUTPUT FORMAT RULES (LinkedIn Post):
# - Maximum 1300 characters including hashtags.
# - Professional tone, no more than 2 emojis total.
# - Short paragraphs (1-3 lines each), plain text, no markdown symbols.
# - End with 3-5 relevant hashtags on a new line, prefixed with "#".
# - Do not include a title or heading line.
# """,

#     "twitter": """
# OUTPUT FORMAT RULES (Twitter/X Post):
# - If content fits in 280 characters, output a single tweet only.
# - If it does not fit, output a thread using EXACTLY this format:

# [TWEET 1]
# <text, max 280 characters including numbering like "1/">
# [TWEET 2]
# <text, max 280 characters>

# - Repeat for each tweet. Maximum 8 tweets in a thread.
# - No markdown, no headings. Hashtags only in the final tweet (max 3).
# """,

#     "instagram": """
# OUTPUT FORMAT RULES (Instagram Post):
# - Start with a short attention-grabbing first line (max 125 characters,
#   this is what shows before "more").
# - Caption body: max 2200 characters total including hashtags.
# - Conversational tone, short line breaks allowed.
# - End with a block of 5-15 relevant hashtags, prefixed with "#", separated
#   by spaces.
# """,

#     "infographic": """
# OUTPUT FORMAT RULES (Infographic Content):
# - Output must contain between 4 and 8 content blocks.
# - Use EXACTLY this format for every block:

# [BLOCK: <short label, max 5 words>]
# <one key statistic, fact or statement, max 20 words>

# - Repeat for every block. Do not add explanations outside this format.
# """,
# }


# def build_transformation_prompt(
#     source_content,
#     audience,
#     objective,
#     tone,
#     language,
#     detail_level,
#     content_style,
#     output_type,
#     additional_instructions
# ):
#     format_rules = OUTPUT_TYPE_RULES.get(output_type, "")

#     prompt = f"""
# Transform the following source content according to the specified
# transformation requirements.

# ================ SOURCE CONTENT ================

# {source_content}

# ================ REQUIREMENTS ================

# Target Audience:
# {audience}

# Communication Objective:
# {objective}

# Tone:
# {tone}

# Language:
# {language}

# Level of Detail:
# {detail_level}

# Content Style:
# {content_style}

# Output Type:
# {output_type}
# ================ ADDITIONAL INSTRUCTIONS ===============
# {additional_instructions if additional_instructions.strip() else "No additional instructions provided."}
# {format_rules}
# ================ TASK ================
# Generate the requested {output_type} using the source content.
# The output must:
# - be suitable for the specified audience
# - fulfil the specified communication objective
# - follow the requested tone and style
# - respect the requested level of detail
# - preserve important factual information
# - avoid unsupported or fabricated information
# - follow the OUTPUT FORMAT RULES exactly
# - follow the additional instructions when provided
# - treat additional instructions as output constraints or requirements
# Return only the final transformed content.
# """
#     return prompt


# SYSTEM_INSTRUCTION = """
# You are an AI-powered content transformation engine.

# Your task is to transform the provided source content into the communication
# artefact requested by the user.

# Follow these rules strictly:

# 1. Preserve the factual meaning of the source content.

# 2. Do not invent facts, names, dates, statistics, events, quotations,
#    organisations, locations, technical details, or recommendations that
#    are not supported by the source.

# 3. Adapt the content according to the following requirements:
#    - Target audience
#    - Communication objective
#    - Tone
#    - Language
#    - Level of detail
#    - Content style
#    - Output type

# 4. Make the output appropriate for the specified target audience.

# 5. Preserve important information from the source while removing
#    irrelevant information when the requested detail level is concise.

# 6. If the source does not contain enough information to support a claim,
#    do not fabricate the missing information.

# 7. Keep the generated content clear, coherent and professionally structured.

# 8. Respect the requested level of detail:
#    - Concise: only the most important information
#    - Moderate: important information with necessary context
#    - Detailed: comprehensive coverage of relevant information

# 9. Follow the structure normally expected for the requested output type.

# 10. Return only the requested transformed content.
#     Do not explain the transformation process.

# 11. Treat all provided transformation parameters as explicit user-selected
# requirements. When the output explicitly refers to any selected parameter,
# use the selected value or its direct wording. Do not replace it with a
# semantic equivalent, broader category, synonym, or inferred audience.
# Do not force the parameter value into places where it is not naturally needed.
# """


# def build_transformation_prompt(
#     source_content,
#     audience,
#     objective,
#     tone,
#     language,
#     detail_level,
#     content_style,
#     output_type,
#     additional_instructions
# ):
#     prompt = f"""
# Transform the following source content according to the specified
# transformation requirements.

# ================ SOURCE CONTENT ================

# {source_content}

# ================ REQUIREMENTS ================

# Target Audience:
# {audience}

# Communication Objective:
# {objective}

# Tone:
# {tone}

# Language:
# {language}

# Level of Detail:
# {detail_level}

# Content Style:
# {content_style}

# Output Type:
# {output_type}

# ================ ADDITIONAL INSTRUCTIONS ================

# {additional_instructions if additional_instructions.strip() else "No additional instructions provided."}


# ================ TASK ================

# Generate the requested {output_type} using the source content.

# The output must:
# - be suitable for the specified audience
# - fulfil the specified communication objective
# - follow the requested tone and style
# - respect the requested level of detail
# - preserve important factual information
# - avoid unsupported or fabricated information
# - follow an appropriate structure for the requested output type
# - follow the additional instructions when provided
# - treat additional instructions as output constraints or requirements

# Return only the final transformed content.
# """

#     return prompt











