---
layout: base
permalink: about/
title: About | Detroit Election Maps
---

# About

This site is an open source, volunteer project to make it easier to access the results of Detroit elections.

## Data access

Detroit Data

## Embed the map

Want to use this on your site? You can embed a responsive iframe with [`pym.js`](https://blog.apps.npr.org/pym.js/).

All you need to do is set up the view that you want on the map page, copy the full URL (including all of the parts after `?` and `#`), and add `embed/` after `detroitelectionmaps.org/`.

As an example, <https://detroitelectionmaps.org/?election=251> would be become <https://detroitelectionmaps.org/embed/?election=251>.

Then, take that URL and copy it into your CMS or site's code in quotes after `data-pym-src` like this:

```html
<div data-pym-title="Title of your embed" data-pym-src="https://detroitelectionmaps.org/embed/...">Loading...</div>
<script type="text/javascript" src="https://pym.nprapps.org/pym.v1.min.js"></script>
```

## Open source

This project is open source under the MIT license and the source code is available on GitHub: [pjsier/detroit-election-maps](https://github.com/pjsier/detroit-election-maps)

## Contact

Other questions or concerns? Feel free to reach out at [info@detroitelectionsarchive.org](mailto:info@detroitelectionsarchive.org)
