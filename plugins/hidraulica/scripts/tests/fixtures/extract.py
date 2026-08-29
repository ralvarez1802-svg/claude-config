import sys
import pypdf
r = pypdf.PdfReader(sys.argv[1])
open(sys.argv[2], "w").write("\n".join(p.extract_text() for p in r.pages))
