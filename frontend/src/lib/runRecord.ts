/** Format a pasteable run record sufficient to replay the run. */
export function formatRunRecord(seed: string, rulesetVersion: string, choiceIds: string[]): string {
  return `seed=${seed} rules=${rulesetVersion} choices=${choiceIds.join(",")}`;
}
