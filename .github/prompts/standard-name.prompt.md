Create a new GitHub issue for iterorganization/IMAS-Standard-Names.

The issue should follow the #file:../ISSUE_TEMPLATE/create-standard-name.yml template.
The issue should include blank lines above and below each section.
The issue should be written in markdown format.
Ensure that the issue is correctly formatted and indented.
Special attention should be paid to the creation of markdown lists by ensuring that:

- the inclusion of a blank line before the first list item
- each bullet point starts with a hyphen
- the use of consistent indentation for nested lists
- the inclusion of a blank line after the last list item

Follow the IMAS Data Dictionary conventions for standard names.
Include the following files as context:

- file:../docs/guidelines.md
- file:../docs/generic_names.csv
- file:../docs/transformations.csv

<!-- retrieve further information about the source  # TODO make  CF Conventions MCP server
[Climate and forecasting conventions](https://cfconventions.org/) upon which the
Fusion Conventions, defined above, are based. In the case of conflicts between the Fusion
and Climate and forecasting conventions, the Fusion conventions take precedence. -->

Use the IMAS MCP server to:

- list schemas
- get schema
- get documentation

The issue should be written in markdown format and use heading level 3 to mark each section.
Ensure that the issue is correctly formatted and indented.
Ensure that the issue is written in Plain English using US spelling.
Use LaTeX formatted math within Markdown for formulas and equations.
Justify all formulas and equations centrally. 
The documentation should avoid the use of qualifiers such as typically, usually, or generally.

Include the following information in the documentation field:

- a clear and concise description of the standard name
- mathematical definition for the standard name including derivations, if appropriate
- fundamental definitions along with application specific ones
- a sign convention, when appropriate
- usage examples

The documentation shall apply to both stellarators and tokamaks. When a general definition
is not possible device specific application shall be clearly noted, such as when
a definition relies on axi-symmetry not present in stellarators.

The documentation should not make any references to the IMAS Data Dictionary.

Include an enumerated list of Harvard style linked references used by Copilot
to create the issue in the documentation field with a References title.

Do not generate images or diagrams.

Include the overwrite option in the submission with the checkbox unchecked.

Create a new section labelled `IMAS Data Dictionary references`.
Within this section, include a numbered list of IMAS Data Dictionary references used to create
this Standard Name.
Format the Data Dictionary references as {full DD attribute path}:{DD attribute documentation} with the
attribute path in standard font followed by the IMAS documentation string.
Separate the path and documentation fields with a colon.

Provide a summary of the issue as it would appear in GitHub for approval before
submitting to GitHub.
Ask for a confirmation to submit the issue to GitHub.
Create the GitHub issue if the user responds in the affirmative.
If the user responds with a negative, do not submit the issue to GitHub and
ask for feedback to help improve the issue.

Before creating the GitHub issue, identify which LLM you are using
(e.g., GPT-4o, Claude 3.5 Sonnet, etc.).

After creating the issue, perform the following steps:

- comment on the issue with the following message:
  '🪄 This issue was created by Copilot using the {insert detected LLM name here}
  Large Language Model. The proposed Standard Name follows the Fusion Conventions. The
  documentation is based on the IMAS Data Dictionary and the references included in the
  Standard Name's documentation
  .'
- Add the "standard-name" label to the submitted issue.

Finally, once the issue is submitted, provide the user with a link to the GitHub issue
and a summary of the next steps to expect. Ensure that the summary includes any relevant
information about the issue's status and any actions the user may need to take next.

Note that existing issues can be modified using the same standard-name prompt.
Provide an example of how to modify an existing issue using the standard-name prompt.
