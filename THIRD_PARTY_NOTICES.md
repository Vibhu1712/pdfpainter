# Third-party notices

pdfpainter does not copy code from these projects; it depends on them at run time.
They are installed separately by pip, under their own licences, listed here for convenience.

## pdfsieve

Apache License 2.0. Copyright 2026 Vaibhav Rawat (AdRaw App Studio).
https://github.com/YOUR-GITHUB-USER/pdfsieve

## pdfminer.six

MIT License. https://github.com/pdfminer/pdfminer.six

```
Copyright (c) 2004-2016  Yusuke Shinyama <yusuke at shinyama dot jp>

Permission is hereby granted, free of charge, to any person
obtaining a copy of this software and associated documentation
files (the "Software"), to deal in the Software without
restriction, including without limitation the rights to use,
copy, modify, merge, publish, distribute, sublicense, and/or
sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following
conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY
KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
```

## Pillow

MIT-CMU License (HPND). Copyright 1997-2011 Secret Labs AB, 1995-2011 Fredrik Lundh and
contributors, 2010 Jeffrey 'Alex' Clark and contributors. https://github.com/python-pillow/Pillow

## NumPy

BSD 3-Clause License. Copyright 2005 NumPy Developers. https://github.com/numpy/numpy

## Test-only dependencies

pytest (MIT) and reportlab (BSD) are used to run the test suite and are not needed to use
pdfpainter. pypdfium2 (Apache-2.0 / BSD-3-Clause) is used, when installed, to compare
page sizes in the tests.
