import { readFileSync } from "fs";
import { setFailed } from "@actions/core";
import { getOctokit, context } from "@actions/github";
import yaml from "js-yaml";

try {
  const fileContents = readFileSync(".github/labels.yml", "utf8");
  const data = yaml.load(fileContents);
  const labels = data.labels;
  const octokit = getOctokit(process.env.GITHUB_TOKEN);

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
