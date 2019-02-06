// WARNING
//
// This file has been generated automatically by Visual Studio to store outlets and
// actions made in the UI designer. If it is removed, they will be lost.
// Manual changes to this file may not be handled correctly.
//
using Foundation;
using System.CodeDom.Compiler;

namespace PresentScreenings.TableView
{
	[Register ("ViewController")]
	partial class ViewController
	{
		[Outlet]
		AppKit.NSTextField BlackLabel { get; set; }

		[Outlet]
		AppKit.NSTextField BlueLabel { get; set; }

		[Outlet]
		AppKit.NSTextField GreyLabel { get; set; }

		[Outlet]
		AppKit.NSTableHeaderView HoursView { get; set; }

		[Outlet]
		AppKit.NSView MainViewControler { get; set; }

		[Outlet]
		AppKit.NSTextField RedLabel { get; set; }

		[Outlet]
		AppKit.NSTableColumn ScreeningsColumn { get; set; }

		[Outlet]
		AppKit.NSTableView ScreeningsTable { get; set; }

		[Outlet]
		AppKit.NSTableColumn ScreensColumn { get; set; }

		//[Action ("ScreeningControlAction:")]
		//partial void ScreeningControlAction (Foundation.NSObject sender);
		
		void ReleaseDesignerOutlets ()
		{
			if (BlackLabel != null) {
				BlackLabel.Dispose ();
				BlackLabel = null;
			}

			if (BlueLabel != null) {
				BlueLabel.Dispose ();
				BlueLabel = null;
			}

			if (GreyLabel != null) {
				GreyLabel.Dispose ();
				GreyLabel = null;
			}

			if (HoursView != null) {
				HoursView.Dispose ();
				HoursView = null;
			}

			if (MainViewControler != null) {
				MainViewControler.Dispose ();
				MainViewControler = null;
			}

			if (RedLabel != null) {
				RedLabel.Dispose ();
				RedLabel = null;
			}

			if (ScreeningsColumn != null) {
				ScreeningsColumn.Dispose ();
				ScreeningsColumn = null;
			}

			if (ScreeningsTable != null) {
				ScreeningsTable.Dispose ();
				ScreeningsTable = null;
			}

			if (ScreensColumn != null) {
				ScreensColumn.Dispose ();
				ScreensColumn = null;
			}
		}
	}
}
