﻿using System;
using AppKit;
using CoreGraphics;
using Foundation;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// Screening label, a lable which is associated with a screening and
    /// displays need-to-know information of that screening.
    /// </summary>

    public class ScreeningLabel : NSTextField
    {
        #region Private Variables
        private Screening _screening = null;
        #endregion

        #region Constructors
        public ScreeningLabel(CGRect frame, Screening screening, bool withDay = false) : base(frame)
        {
            Initialize();
            _screening = screening;
            Font = ControlsFactory.StandardBoldFont;
            Editable = false;
            Bordered = false;
            StringValue = _screening.ToScreeningLabelString(withDay);
            LineBreakMode = NSLineBreakMode.TruncatingMiddle;
            ColorView.SetScreeningColor(_screening, this);
            NeedsDisplay = true;
        }

        void Initialize()
        {
            // Initialize draw properties.
            WantsLayer = true;
            LayerContentsRedrawPolicy = NSViewLayerContentsRedrawPolicy.OnSetNeedsDisplay;
        }
        #endregion

        #region Override Methods
        /// <summary>
        /// Override the MouseDown event by a no-op to prevent undesired
        /// behaviour when a Screening Label overlaps the clickable control
        /// rectangle of another Screening Control.
        /// </summary>
        /// <param name="theEvent"></param>

        public override void MouseDown(NSEvent theEvent)
        {
        }
        #endregion
    }
}
