import type { ToolDefinition } from "../types.js";

interface GetCurrentTimeArgs {
  timezone?: string;
}

export const getCurrentTimeTool: ToolDefinition<GetCurrentTimeArgs> = {
  name: "get_current_time",
  description:
    "Returns the current date, time, day of the week, and timezone. Useful when answering questions about what time or date it is.",
  parameters: {
    type: "object",
    properties: {
      timezone: {
        type: "string",
        description:
          "Optional IANA timezone string, such as 'UTC', 'America/New_York', 'Asia/Riyadh', 'Europe/London', etc. Defaults to system local timezone.",
      },
    },
    required: [],
  },
  execute: (args) => {
    const now = new Date();
    const timeZone = args.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";

    try {
      const formatted = new Intl.DateTimeFormat("en-US", {
        timeZone,
        dateStyle: "full",
        timeStyle: "long",
      }).format(now);

      const iso = now.toISOString();

      return {
        success: true,
        timezone: timeZone,
        iso_timestamp: iso,
        human_readable: formatted,
        epoch_ms: now.getTime(),
      };
    } catch (err) {
      // Fallback in case of invalid timezone
      return {
        success: true,
        timezone: "UTC",
        iso_timestamp: now.toISOString(),
        human_readable: now.toUTCString(),
        epoch_ms: now.getTime(),
        note: `Timezone '${args.timezone}' was invalid, defaulted to UTC.`,
      };
    }
  },
};
