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
	[Register ("AnalyserDialogController")]
	partial class AnalyserDialogController
	{
		[Outlet]
		AppKit.NSOutlineView _filmOutlineView { get; set; }

		[Outlet]
		AppKit.NSTableColumn _filmsColumn { get; set; }

		[Outlet]
		AppKit.NSTableColumn _infoColumn { get; set; }
		
		void ReleaseDesignerOutlets ()
		{
			if (_filmOutlineView != null) {
				_filmOutlineView.Dispose ();
				_filmOutlineView = null;
			}

			if (_filmsColumn != null) {
				_filmsColumn.Dispose ();
				_filmsColumn = null;
			}

			if (_infoColumn != null) {
				_infoColumn.Dispose ();
				_infoColumn = null;
			}
		}
	}
}
