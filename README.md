# datacost

**How many shillings does one visit to a website really cost you?**

Most people in Uganda pay for data by the megabyte, but nobody sees what a web page actually downloads. `datacost` opens a page, adds up everything it loads (images, scripts, styles, media), and tells you the price of one visit in UGX. Give it several sites and it ranks them from most to least expensive.

## Run it

You only need Python 3. No extra libraries.

One page, detailed breakdown:

```
python datacost.py https://example.com
```

Several pages, ranked table:

```
python datacost.py https://site1.com https://site2.com https://site3.com
```

Use your own bundle price:

```
python datacost.py https://example.com --bundle-mb 1000 --bundle-ugx 5000
```

## Example output

One page:

```
What this page downloads
----------------------------------------
  image             585.9 KB
  script             39.1 KB
  page (html)         0.2 KB
----------------------------------------
  TOTAL             625.2 KB

  One visit costs about   3.1 UGX
  10 visits a day, a month (300 visits): 916 UGX
  One bundle gives you only 1,638 visits
```

Several pages:

```
Ranked: most expensive page first
----------------------------------------------------------------------
  #  Page                                        Size   Cost/visit
----------------------------------------------------------------------
  1  site-a.com                              2.40 MB     11.7 UGX
  2  site-b.com                            310.0 KB      1.5 UGX
----------------------------------------------------------------------
```

(Replace these with real screenshots from sites you tested.)

## How it works

1. Downloads the page HTML.
2. Finds the images, scripts, stylesheets and media it links to.
3. Downloads each one and adds up the bytes actually transferred (compressed size, like a phone would receive).
4. Converts the total to shillings using your bundle size and price.

## Limits

- It does not run JavaScript, so content loaded later (feeds, video, ads) is **not counted**. Real cost is usually higher.
- The default bundle (1000 MB for 5,000 UGX) is only an example. Set your own.

## Ideas to extend it

- Publish a "most expensive pages" table for popular Ugandan sites.
- Add a simple web page for it.
- Add a chart comparing sites.

## License

MIT
