function die(msg) {
  print(msg);
  quit();
}

function toCharCode(c) {
  return c.charCodeAt(0);
}

function bufSearch(buf, needle, options) {
  options = options || {};
  var start = options.start || 0;
  var end = options.end || buf.length;
  if (typeof needle === 'string') {
    needle = Array.prototype.map.call(needle, toCharCode);
  }
  for (var i = start; i < end; i++) {
    for (var j = 0; j < needle.length; j++) {
      if (buf[i + j] !== needle[j]) {
        break;
      }
      if (j === needle.length - 1) {
        return i;
      }
    }
  }
  return null;
}

function bufSearchBack(buf, needle, options) {
  options = options || {};
  var start = options.start || buf.length;
  var end = options.end || 0;
  if (typeof needle === 'string') {
    needle = Array.prototype.map.call(needle, toCharCode);
  }
  needle.reverse();
  for (var i = start - 1; i >= end; i--) {
    for (var j = 0; j < needle.length; j++) {
      if (buf[i - j] !== needle[j]) {
        break;
      }
      if (j === needle.length - 1) {
        return i;
      }
    }
  }
  return null;
}

function bufFill(buf, options) {
  options = options || {};
  var start = options.start || 0;
  var end = options.end || buf.length;
  var char = options.char || ' '.charCodeAt(0);
  for (var i = start; i < end; i++) {
    buf[i] = char
  }
}

function processPageAnnotations(page) {
  var annotationsArray = page.Annots;
  if (annotationsArray && annotationsArray.isArray()) {
    cleanAnnotations(annotationsArray);
  }
  if (annotationsArray.length === 0) {
    page.delete('Annots');
  }
}

function cleanAnnotations(annotationsArray) {
  var toClean = findAnnotations(annotationsArray);
  toClean.reverse(); // delete in reverse order otherwise the indexes get messed up
  toClean.forEach(function(i) { annotationsArray.delete(i) })
}

function findAnnotations(annotationsArray) {
  var toClean = [];
  function check(index, annotation) {
    if (!annotation.isDictionary()) {
      return;
    }
    var a = annotation.A;
    if (!a || !a.isDictionary()) {
      return;
    }
    var uri = a.URI;
    if (!uri || uri.toString() !== '(https://www.tracker-software.com/product/pdf-xchange-editor)') {
      return;
    }
    toClean.push(index);
  }
  annotationsArray.forEach(check)
  return toClean;
}

function processPageXObjects(page) {
  var resources = page.Resources;
  if (resources && resources.isDictionary()) {
    var xobjectsDict = resources.XObject;
    if (xobjectsDict && xobjectsDict.isDictionary()) {
      var xobjectNames = findXObjects(xobjectsDict);
      cleanXObjects(xobjectsDict, xobjectNames);
      if (!xobjectsDict.length) {
        page.delete('XObject');
      }
    }
    return xobjectNames;
  }
}

function findXObjects (xobjectsDict) {
  var xobjectNames = [];
  function check(key, xobject) {
    if (!xobject || !xobject.isStream()) {
      return;
    }
    var stream = xobject.readStream();
    if (bufSearch(stream, 'Click to BUY NOW!')) {
      xobjectNames.push(key);
    }
  }
  xobjectsDict.forEach(check);
  return xobjectNames;
}

function cleanXObjects(xobjectsDict, xobjectNames) {
  xobjectNames.forEach(function(x) { xobjectsDict.delete(x) });
}

function processPageContentStream(page, xobjectNames) {
  var pageContent = page.Contents;
  if (pageContent && pageContent.isStream()) {
    var contentBuf = pageContent.readStream();
    if (contentBuf) {
      xobjectNames.forEach(function(name) { cleanStream(contentBuf, name) });
      pageContent.writeStream(contentBuf);
    }
  }
}

function cleanStream(pageBuffer, xobjectName) {
  var search1 = '/' + xobjectName + ' Do';
  var search2 = '/Artifact';
  var search3 = 'EMC';
  var found1, found2, found3;
  var start = 0;
  do {
    found1 = bufSearch(pageBuffer, search1, {
      start: start
    });
    if (found1) {
      start = found1 + search1.length;
      found2 = bufSearchBack(pageBuffer, search2, {
        start: found1
      });
      found3 = bufSearch(pageBuffer, 'EMC', {
        start: start
      });
      if (!found2 || !found3) {
        print('Something went wrong cleaning stream, can\'t find watermark boundaries');
      } else {
        bufFill(pageBuffer, {
          start: found2 - search2.length,
          end: found3 + search3.length
        });
      }
    }
    found2 = found3 = null;
  } while (found1);
}

var scriptname = 'pdfxchange.js'

if (scriptArgs.length < 2) {
  die('Not enough arguments\nUsage:\n\tmutool run ' + scriptname + ' <input.pdf> <output.pdf>');
}

function cleanPage(page) {
  processPageAnnotations(page);
  var xobjectNames = processPageXObjects(page);
  if (xobjectNames && xobjectNames.length) {
    processPageContentStream(page, xobjectNames);
  }
}

var pdf = new PDFDocument(scriptArgs[0]);

var pageCount = pdf.countPages();

for (var i = 0; i < pageCount; i++) {
  var page = pdf.findPage(i);
  cleanPage(page);
}

pdf.save(scriptArgs[1]);
