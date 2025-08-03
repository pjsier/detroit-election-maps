import EleventyVitePlugin from "@11ty/eleventy-plugin-vite"
import solidPlugin from "vite-plugin-solid"

export default function (eleventyConfig) {
  eleventyConfig.addPlugin(EleventyVitePlugin, {
    viteOptions: {
      plugins: [solidPlugin()],
    },
  })

  eleventyConfig.addPassthroughCopy({ src: "assets" })

  return {
    dir: {
      input: "site/",
      output: "dist",
      includes: "_includes",
      layouts: "_layouts",
    },
    templateFormats: ["html", "md", "njk"],
    htmlTemplateEngine: "njk",
    passthroughFileCopy: true,
  }
}
