import { readFileSync } from "fs";
import { setFailed } from "@actions/core";
import { getOctokit, context } from "@actions/github";
import yaml from "js-yaml";

try {
  const fileContents = readFileSync(".github/labels.yml", "utf8");
  const data = yaml.load(fileContents);
  const labels = data.labels;
  const octokit = getOctokit(process.env.GITHUB_TOKEN);

  // Create a set of label names from the YAML file for quick lookup
  const configuredLabelNames = new Set(labels.map((label) => label.name));

  // First, get all existing labels in the repository
  console.log("Fetching existing repository labels...");
  const existingLabelsResponse = await octokit.rest.issues.listLabelsForRepo({
    ...context.repo,
    per_page: 100,
  });

  // Check for and delete labels that exist in repo but not in config
  for (const existingLabel of existingLabelsResponse.data) {
    if (!configuredLabelNames.has(existingLabel.name)) {
      console.log(
        `Deleting label '${existingLabel.name}' as it's not in the configuration...`
      );
      try {
        await octokit.rest.issues.deleteLabel({
          ...context.repo,
          name: existingLabel.name,
        });
        console.log(`Label '${existingLabel.name}' deleted successfully.`);
      } catch (error) {
        console.error(
          `Error deleting label '${existingLabel.name}': ${error.message}`
        );
      }
    }
  }

  // Create or update labels from the configuration
  console.log("Creating or updating configured labels...");
  for (const label of labels) {
    try {
      await octokit.rest.issues.createLabel({
        ...context.repo,
        name: label.name,
        color: label.color.replace("#", ""),
        description: label.description,
      });
      console.log(`Label '${label.name}' created successfully.`);
    } catch (error) {
      if (error.status === 422) {
        console.log(`Label '${label.name}' already exists. Updating...`);
        await octokit.rest.issues.updateLabel({
          ...context.repo,
          name: label.name,
          color: label.color.replace("#", ""),
          description: label.description,
        });
        console.log(`Label '${label.name}' updated successfully.`);
      } else {
        console.error(`Error with label '${label.name}': ${error.message}`);
      }
    }
  }
} catch (error) {
  setFailed(`Action failed with error: ${error}`);
}
