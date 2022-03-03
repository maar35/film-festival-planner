using AppKit;
using CoreGraphics;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// Screenings table row view, resposible for actions on entire rows in the
    /// screenings table.
    /// Overridden to minimize flicker effects when a row is automatically
    /// deselected.
    /// </summary>

    public class ScreenigsTableRowView : NSTableRowView
    {
        #region Override Methods
        public override void DrawSelection(CGRect dirtyRect)
        {
            if (SelectionHighlightStyle != NSTableViewSelectionHighlightStyle.None)
            {
                NSColor.Clear.SetStroke();
                NSColor.Clear.SetFill();
                var selectionPath = NSBezierPath.FromRoundedRect(dirtyRect, 0, 0);
                selectionPath.Fill();
                selectionPath.Stroke();
            }
        }
        #endregion
    }
}
