from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
import tempfile

doc = SimpleDocTemplate('test_pdf.pdf')
styles = getSampleStyleSheet()

from PIL import Image
img = Image.new('RGB', (50, 20), color = (73, 109, 137))
img.save('dummy.png')

story = []
text = 'Here is some text with an inline image <img src="dummy.png" width="50" height="20" valign="-5"/> inside it. It should align perfectly.'
story.append(Paragraph(text, styles['Normal']))
doc.build(story)
print('PDF generated successfully')
