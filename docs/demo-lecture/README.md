# Demo lecture: Regression, risk & loss

The lecture LectureLoop uses in mock mode and in demos. It was written by the LectureLoop team so the
repo carries no third-party course material: every sentence, example, figure, dataset and question is
our own, and the ferry, tide and lateness data are synthetic.

The topics follow a standard intro-ML sequence, and each concept sits on the same page number the
concept graph expects (`backend/tests/fixtures/gold/cs3151_m04.json`, `frontend/lib/mock/data.ts`).
If you move a topic to another page, update both files.

## Rebuild

```bash
pip install matplotlib numpy scikit-learn pillow
python build_lecture.py out/            # all 36 pages
python build_lecture.py out/ 6 12 17    # only some pages, for a quick look
```

This writes `out/lectureloop_demo_regression.pdf` and `out/<page>.jpg` (1200 × 800). To refresh the
app, copy the JPGs to `frontend/public/mock-pages/` and the PDF here. The Inter font is used if
installed; otherwise matplotlib falls back to DejaVu Sans.

## License

Text, figures and data: CC BY 4.0, LectureLoop team.
