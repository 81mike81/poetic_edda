import json, codecs
import re
import sys

input = sys.argv[1]
output = sys.argv[2]

answers = None
if len(sys.argv) > 3:
	answers = list(sys.argv[3])

f = codecs.open(input, 'r', 'utf-8')
blocks = f.read().split(u"\n\n")
f.close()

# remove page marks
blocks = [x for x in blocks if not re.match(ur'^p\. \d+', x)]

# glue blocks, mark stanzas and comments
new_blocks = []
comments = []

def processBlock(b):

	if b.startswith(u'['):
		b = b[1:]
	if b.endswith(u']'):
		b = b[:-1]

	lines = b.split(u"\n")

	mo = re.match(ur'^Prose\. ', lines[0])
	if mo is not None:
		return {'type': 'prose comment', 'text': b[7:]}

	mo = re.match(ur'^(\d+)\. ', lines[0])

	if mo is not None:
		number = mo.group(1)
		return {'type': 'stanza', 'number': int(number),
			'text': u"\n".join([lines[0][len(number) + 2:]] + lines[1:]), 'comment': None}

	if len(lines) > 1:
		mo = re.match(ur'^(\d+)\. ', lines[1])
		if mo is not None:
			number = mo.group(1)
			return {'type': 'stanza', 'number': int(number),
				'text': u"\n".join([lines[1][len(number) + 2:]] + lines[2:]),
				'prelude': lines[0], 'comment': None}

	return {'type': 'text', 'text': b}


comment_area = False
for block in blocks:
	if block.startswith(u'['):
		comment_area = True

	obj = processBlock(block)

	if not comment_area:
		if obj['type'] == 'stanza':
			new_blocks.append(obj)
		elif u'|' in obj['text'] or len(obj['text'].split('\n')) > 1:
			new_blocks[-1]['text'] += u'\n' + obj['text']
		elif len(new_blocks) == 0:
			new_blocks.append({'type': 'prose', 'text': obj['text'], 'comment': None})
		else:
			if answers is not None:
				s = answers.pop(0)
			else:
				print "* Previous text:\n" + new_blocks[-1]['text'] + \
					"\n* Current text:\n" + obj['text']

				s = raw_input("(p) new prose, (c) continuation? ")
			if s.startswith('p'):
				new_blocks.append({'type': 'prose', 'text': obj['text'], 'comment': None})
			else:
				new_blocks[-1]['text'] += u'\n' + obj['text']
	else:
		if obj['type'] == 'prose comment':
			for i in xrange(len(new_blocks) - 1, -1, -1):
				if new_blocks[i]['type'] == 'prose':
					new_blocks[i]['comment'] = obj['text']
					break
		elif obj['type'] == 'stanza':
			comments.append(obj)
		else:
			comments[-1]['text'] = comments[-1]['text'] + "\n" + obj['text']

	if block.endswith(u']'):
		comment_area = False

for obj in comments:
	for block in new_blocks:
		if 'number' in block and block['number'] == obj['number']:
			block['comment'] = obj['text']
			break
	else:
		raise Exception(obj)



def processStanza(t):
	t = re.sub(ur'"([^"]+)"', ur"``\1''", t)
	return t.replace(u" | ", u"{\\sep}").split(u'\n')

def processProse(t):
	t = re.sub(ur'"([^"]+)"', ur"``\1''", t)
	t = re.sub(ur'\.\s+', u'.\n', t)
	return t.split(u'\n')

def processComment(t):

	def subfun(mo):
		if mo.group(1) == u'cf':
			return u'cf. '
		elif mo.group(1) == u'Cf':
			return u'Cf. '
		else:
			return mo.group(1) + u'.\n'

	t = re.sub(ur'\s*\[fp\. \d+\]\s*', u' ', t)
	t = re.sub(ur'"([^"]+)"', ur"``\1''", t)
	t = re.sub(ur'([\w\)]+)\. ', subfun, t)
	return t.split(u'\n')


c = []
for block in new_blocks:
	if 'text' in block:
		if block['type'] == 'stanza':
			block['text'] = processStanza(block['text'])
		else:
			block['text'] = processProse(block['text'])

	if 'comment' in block and block['comment'] is not None:
		block['comment'] = processComment(block['comment'])

	if block['type'] == 'stanza':
		translation = block['text']
		original = []

		for line in translation:
			if u'{\\sep}' in line:
				original.append(u"{\\sep}")
			else:
				original.append(u"")

		if 'prelude' in block:
			c.append({
				'type': 'stanza pair',
				'original': original,
				'original_prelude': [u""],
				'comment': block['comment'],
				'translation': translation,
				'translation_prelude': [block['prelude']],
				'number': block['number']
			})
		else:
			c.append({
				'type': 'stanza pair',
				'original': original,
				'comment': block['comment'],
				'translation': translation,
				'number': block['number']
			})
	elif block['type'] == 'prose':
		translation = block['text']
		original = [u""] * len(translation)
		c.append({
			'type': 'prose',
			'comment': block['comment'],
			'original': original,
			'translation': translation
		})
	else:
		raise Exception(repr(block))


f = codecs.open(output, 'w', 'utf-8')
json.dump(c, f, indent=4, ensure_ascii=False)
f.close()