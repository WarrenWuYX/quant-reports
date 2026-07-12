import { defineCollection, z } from "astro:content";

const analyses = defineCollection({
  type: "data",
  schema: z.object({
    schema_version: z.string(),
    slug: z.string(),
    status: z.string(),
    confidence: z.string(),
    model_used: z.string(),
    source: z.object({
      title: z.string(),
      institution: z.string(),
      authors: z.array(z.string()).default([]),
      published: z.string().nullable().optional(),
      source_type: z.string(),
      original_url: z.string().nullable().optional(),
      local_path: z.string(),
      ingested_at: z.string(),
    }),
    classification: z.object({
      research_type: z.array(z.string()).default([]),
      data_frequency: z.array(z.string()).default([]),
      factor_family: z.array(z.string()).default([]),
      asset_class: z.array(z.string()).default([]),
      method: z.array(z.string()).default([]),
      custom_tags: z.array(z.string()).default([]),
    }).default({}),
    ratings: z.object({
      quality: z.number().int().min(1).max(5),
      novelty: z.number().int().min(1).max(5),
      reusability: z.number().int().min(1).max(5),
    }),
    concise: z.object({
      one_liner: z.string(),
      core_points: z.array(z.string()).default([]),
      key_result: z.string(),
    }),
    detailed: z.object({
      core_content: z.string(),
      economic_logic: z.string(),
      construction: z.object({
        type: z.string(),
        data_inputs: z.array(z.record(z.unknown())).default([]),
        backtest_setup: z.record(z.unknown()).nullable().optional(),
        combination: z.string().nullable().optional(),
        parameters: z.array(z.record(z.unknown())).default([]),
        factor_definition: z.string().nullable().optional(),
        processing_pipeline: z.array(z.string()).default([]),
        model_architecture: z.string().nullable().optional(),
        inputs: z.array(z.string()).default([]),
        outputs: z.string().nullable().optional(),
        training: z.string().nullable().optional(),
        strategy_logic: z.string().nullable().optional(),
        allocation: z.string().nullable().optional(),
      }),
      excess_return_logic: z.string(),
      performance: z.object({
        metrics: z.array(z.object({ name: z.string(), value: z.string() })).default([]),
        benchmark: z.string().nullable().optional(),
        backtest_period: z.string().nullable().optional(),
        turnover: z.string().nullable().optional(),
        capacity: z.string().nullable().optional(),
        ic_decay: z.string().nullable().optional(),
        summary: z.string().default(""),
      }),
      attribution: z.object({
        done: z.boolean(),
        method: z.string().nullable().optional(),
        summary: z.string(),
        gap: z.string().nullable().optional(),
      }),
      robustness: z.object({
        subsample_stability: z.string().nullable().optional(),
        style_bias: z.string().nullable().optional(),
        turnover: z.string().nullable().optional(),
        capacity: z.string().nullable().optional(),
        summary: z.string().default(""),
      }).default({}),
      data_dependency: z.object({
        data_required: z.string().default(""),
        reproducibility: z.string().default(""),
        summary: z.string().default(""),
      }).default({}),
      prior_art: z.array(z.object({
        method: z.string(),
        relation: z.string().default(""),
      })).default([]),
      novelty_assessment: z.object({
        type: z.string(),
        summary: z.string(),
      }),
    }),
    critical: z.object({
      weaknesses: z.array(z.string()).default([]),
      useful_elements: z.array(z.string()).default([]),
      inspirations: z.array(z.string()).default([]),
      improvement_ideas: z.array(z.object({
        idea: z.string(),
        based_on: z.string().default(""),
        expected_gain: z.string().default(""),
      })).default([]),
      replication_plan: z.string().default(""),
    }).default({}),
    entities: z.array(z.object({
      name: z.string(),
      type: z.string(),
    })).default([]),
    related_reports: z.array(z.object({
      slug: z.string(),
      title: z.string(),
      relation: z.string().default(""),
    })).default([]),
  }),
});

export const collections = { analyses };