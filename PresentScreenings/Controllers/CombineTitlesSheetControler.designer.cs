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
	[Register ("CombineTitleViewControler")]
	partial class CombineTitlesSheetController
	{
		[Outlet]
		AppKit.NSScrollView _screeningsScrollView { get; set; }

		[Outlet]
		AppKit.NSTextField _titleLabel { get; set; }

		[Action ("AcceptSheet:")]
		partial void AcceptSheet (Foundation.NSObject sender);

		[Action ("CancelSheet:")]
		partial void CancelSheet (Foundation.NSObject sender);
		
		void ReleaseDesignerOutlets ()
		{
			if (_screeningsScrollView != null) {
				_screeningsScrollView.Dispose ();
				_screeningsScrollView = null;
			}

			if (_titleLabel != null) {
				_titleLabel.Dispose ();
				_titleLabel = null;
			}
		}
	}
}
