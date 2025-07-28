import EleventyVitePlugin from "@11ty/eleventy-plugin-vite"
import solidPlugin from "vite-plugin-solid"
import Image from "@11ty/eleventy-img"

async function resizeImage(src, sizes, outputFormat = "png") {
  const stats = await Image(src, {
    widths: [+sizes.split("x")[0]],
    formats: [outputFormat],
    outputDir: "./site/img",
  })

  const props = stats[outputFormat].slice(-1)[0]
  return props.url
}

export default function (eleventyConfig) {
  eleventyConfig.addPlugin(EleventyVitePlugin, {
    viteOptions: {
      plugins: [solidPlugin()],
    },
  })

  eleventyConfig.addNunjucksAsyncShortcode("resizeImage", resizeImage)
  eleventyConfig.addFilter("resizeImage", resizeImage)

  // TODO: Check if this triggers hot reloading?
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
