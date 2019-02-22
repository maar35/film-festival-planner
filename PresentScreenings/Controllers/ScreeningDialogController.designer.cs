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
	[Register ("ScreeningDialogController")]
	partial class ScreeningDialogController
	{
		[Outlet]
		Foundation.NSObject _buttonIAttend { get; set; }

		[Outlet]
		AppKit.NSButton _checkboxIAttend { get; set; }

		[Outlet]
		AppKit.NSButton _checkboxSoldOut { get; set; }

		[Outlet]
		AppKit.NSButtonCell _checkboxTicketsBought { get; set; }

		[Outlet]
		AppKit.NSComboBox _comboboxRating { get; set; }

		[Outlet]
		AppKit.NSButton _filmInfoButton { get; set; }

		[Outlet]
		AppKit.NSTextField _labelPresent { get; set; }

		[Outlet]
		AppKit.NSTextField _labelScreen { get; set; }

		[Outlet]
		AppKit.NSTextField _labelTime { get; set; }

		[Outlet]
		AppKit.NSTextField _labelTitle { get; set; }

		[Action ("AcceptDialog:")]
		partial void AcceptDialog (Foundation.NSObject sender);

		[Action ("CancelDialog:")]
		partial void CancelDialog (Foundation.NSObject sender);

		[Action ("DisplayScreeningInfo:")]
		partial void DisplayScreeningInfo (Foundation.NSObject sender);

		[Action ("IAttendScreening:")]
		partial void IAttendScreening (Foundation.NSObject sender);

		[Action ("SetRating:")]
		partial void SetRating (Foundation.NSObject sender);

		[Action ("ToggleSoldOut:")]
		partial void ToggleSoldOut (Foundation.NSObject sender);

		[Action ("ToggleTicketsBought:")]
		partial void ToggleTicketsBought (Foundation.NSObject sender);
		
		void ReleaseDesignerOutlets ()
		{
			if (_buttonIAttend != null) {
				_buttonIAttend.Dispose ();
				_buttonIAttend = null;
			}

			if (_checkboxIAttend != null) {
				_checkboxIAttend.Dispose ();
				_checkboxIAttend = null;
			}

			if (_checkboxSoldOut != null) {
				_checkboxSoldOut.Dispose ();
				_checkboxSoldOut = null;
			}

			if (_checkboxTicketsBought != null) {
				_checkboxTicketsBought.Dispose ();
				_checkboxTicketsBought = null;
			}

			if (_comboboxRating != null) {
				_comboboxRating.Dispose ();
				_comboboxRating = null;
			}

			if (_labelPresent != null) {
				_labelPresent.Dispose ();
				_labelPresent = null;
			}

			if (_labelScreen != null) {
				_labelScreen.Dispose ();
				_labelScreen = null;
			}

			if (_labelTime != null) {
				_labelTime.Dispose ();
				_labelTime = null;
			}

			if (_labelTitle != null) {
				_labelTitle.Dispose ();
				_labelTitle = null;
			}

			if (_filmInfoButton != null) {
				_filmInfoButton.Dispose ();
				_filmInfoButton = null;
			}
		}
	}
}
