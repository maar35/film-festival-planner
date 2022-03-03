using AppKit;
using CoreGraphics;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// Film table row view, responsible for actions on the entire row in the
    /// film rating table.
    /// Overridden to change the standard selection color blue into something
    /// that keeps all subselection labels readable.
    /// </summary>

    public class FilmTableRowView : NSTableRowView
    {
        #region Ovderide Methods
        public override void DrawSelection(CGRect dirtyRect)
        {
            if (SelectionHighlightStyle != NSTableViewSelectionHighlightStyle.None)
            {
                NSColor.FromCalibratedWhite(0.65f, 1.0f).SetStroke();
                NSColor.FromCalibratedWhite(0.82f, 1.0f).SetFill();
                var selectionPath = NSBezierPath.FromRoundedRect(dirtyRect, 0, 0);
                selectionPath.Fill();
                selectionPath.Stroke();
            }
        }
        #endregion
    }
}
