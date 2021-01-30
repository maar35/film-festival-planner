using System.Collections.Generic;
using System;
using AppKit;
using CoreGraphics;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// Color view, provides the dedicated colors for representation of a screening.
    /// </summary>
    /// 
    /// Could be refactored as to work with color-pairs (text-backgound).

    public static class ColorView
    {
        #region Private members
        static readonly NSColor screeningBgColorBlack = NSColor.FromRgb(0, 0, 0);
        static readonly NSColor screeningTextColorBlack = NSColor.White;
        static readonly NSColor screeningBgColorGrey = NSColor.FromRgb(219, 219, 219);
        static readonly NSColor screeningTextColorGrey = NSColor.FromRgb(0, 0, 0);
        static readonly NSColor screeningBgColorDarkGrey = NSColor.FromRgb(176, 176, 176);
        static readonly NSColor screeningTextColorDarkGrey = NSColor.FromRgb(0, 0, 0);
        static readonly NSColor screeningBgColorBlue = NSColor.FromRgb(0, 38, 176);
        static readonly NSColor screeningTextColorBlue = NSColor.FromRgb(255, 255, 255);
        static readonly NSColor screeningBgColorRed = NSColor.FromRgb(176, 0, 38);
        static readonly NSColor screeningTextColorRed = NSColor.White;
        static readonly NSColor screeningBgColorBrightRed = NSColor.FromRgb(255, 38, 0);
        static readonly NSColor screeningTextColorBrightRed = NSColor.FromRgb(0, 217, 255);
        static readonly NSColor screeningBgColorGreen = NSColor.FromRgb(0, 255, 38);
        static readonly NSColor screeningTextColorGreen = NSColor.FromRgb(255, 0, 217);
        static readonly NSColor screeningBgColorPurple = NSColor.FromRgb(176, 0, 176);
        static readonly NSColor screeningTextColorPurple = NSColor.White;
        static readonly NSColor screeningBgColorAqua = NSColor.FromRgb(38, 255, 176);
        static readonly NSColor screeningTextColorAqua = NSColor.Black;
        static readonly Dictionary<ScreeningInfo.ScreeningStatus, NSColor> TextColorByScreeningStatus;
        static readonly Dictionary<ScreeningInfo.ScreeningStatus, NSColor> BgColorByScreeningStatus;
        static readonly Dictionary<ScreeningInfo.TicketsStatus, NSColor> ColorByTicketStatus;
        static readonly NSColor ClickPadColorBlue = NSColor.FromRgba(0, 0, 255, 207);
        static readonly NSColor ClickPadColorGreen = NSColor.FromRgba(0, 127, 0, 207);
        static readonly NSColor ClickPadColorGrey = NSColor.FromRgba(127, 127, 127, 119);
        static readonly NSColor ClickPadColorPeach = NSColor.FromRgba(255, 217, 176, 207);
        static readonly NSColor ClickPadTextColorSelected = NSColor.White;
        static readonly NSColor ClickPadTextColorUnselected = NSColor.Red;
        static readonly Dictionary<Tuple<bool, bool>, NSColor> clickPadColorByVodSelected;
        static readonly NSColor soldOutColorSelected = NSColor.FromRgb(219, 176, 38);
        static readonly NSColor soldOutColorUnselected = NSColor.FromRgb(176, 79, 38);
        #endregion

        #region Constructors
        static ColorView()
        {
            clickPadColorByVodSelected = new Dictionary<Tuple<bool, bool>, NSColor> { };
            clickPadColorByVodSelected[new Tuple<bool, bool>(false, false)] = ClickPadColorGrey;
            clickPadColorByVodSelected[new Tuple<bool, bool>(false, true)] = ClickPadColorBlue;
            clickPadColorByVodSelected[new Tuple<bool, bool>(true, false)] = ClickPadColorPeach;
            clickPadColorByVodSelected[new Tuple<bool, bool>(true, true)] = ClickPadColorGreen;

            TextColorByScreeningStatus = new Dictionary<ScreeningInfo.ScreeningStatus, NSColor> { };
            TextColorByScreeningStatus.Add(ScreeningInfo.ScreeningStatus.Free, screeningTextColorBlack);
            TextColorByScreeningStatus.Add(ScreeningInfo.ScreeningStatus.NeedingTickets, screeningTextColorPurple);
            TextColorByScreeningStatus.Add(ScreeningInfo.ScreeningStatus.Attending, screeningTextColorRed);
            TextColorByScreeningStatus.Add(ScreeningInfo.ScreeningStatus.AttendedByFriend, screeningTextColorBlue);
            TextColorByScreeningStatus.Add(ScreeningInfo.ScreeningStatus.AttendingFilm, screeningTextColorGrey);
            TextColorByScreeningStatus.Add(ScreeningInfo.ScreeningStatus.TimeOverlap, screeningTextColorGrey);
            TextColorByScreeningStatus.Add(ScreeningInfo.ScreeningStatus.NoTravelTime, screeningTextColorDarkGrey);
            TextColorByScreeningStatus.Add(ScreeningInfo.ScreeningStatus.OnLine, screeningTextColorBrightRed);
            TextColorByScreeningStatus.Add(ScreeningInfo.ScreeningStatus.SeeOnLine, screeningTextColorGreen);

            BgColorByScreeningStatus = new Dictionary<ScreeningInfo.ScreeningStatus, NSColor> { };
            BgColorByScreeningStatus.Add(ScreeningInfo.ScreeningStatus.Free, screeningBgColorBlack);
            BgColorByScreeningStatus.Add(ScreeningInfo.ScreeningStatus.NeedingTickets, screeningBgColorPurple);
            BgColorByScreeningStatus.Add(ScreeningInfo.ScreeningStatus.Attending, screeningBgColorRed);
            BgColorByScreeningStatus.Add(ScreeningInfo.ScreeningStatus.AttendedByFriend, screeningBgColorBlue);
            BgColorByScreeningStatus.Add(ScreeningInfo.ScreeningStatus.AttendingFilm, NSColor.Yellow);
            BgColorByScreeningStatus.Add(ScreeningInfo.ScreeningStatus.TimeOverlap, screeningBgColorGrey);
            BgColorByScreeningStatus.Add(ScreeningInfo.ScreeningStatus.NoTravelTime, screeningBgColorDarkGrey);
            BgColorByScreeningStatus.Add(ScreeningInfo.ScreeningStatus.OnLine, screeningBgColorBrightRed);
            BgColorByScreeningStatus.Add(ScreeningInfo.ScreeningStatus.SeeOnLine, screeningBgColorGreen);

            ColorByTicketStatus = new Dictionary<ScreeningInfo.TicketsStatus, NSColor> { };
            ColorByTicketStatus.Add(ScreeningInfo.TicketsStatus.TicketsArranged, screeningBgColorRed);
            ColorByTicketStatus.Add(ScreeningInfo.TicketsStatus.NoTicketsNeeded, screeningBgColorBlack);
            ColorByTicketStatus.Add(ScreeningInfo.TicketsStatus.MustBuyTickets, screeningBgColorPurple);
            ColorByTicketStatus.Add(ScreeningInfo.TicketsStatus.MustSellTickets, screeningBgColorAqua);
        }
        #endregion

        #region Public members
        public static void SetScreeningColor(Screening screening, NSTextField label)
        {
            var status = screening.Status;
            label.BackgroundColor = BgColorByScreeningStatus[status];
            label.TextColor = TextColorByScreeningStatus[status];
        }

        public static void SetScreeningColor(Screening screening, CGContext context)
        {
            var status = screening.Status;
            context.SetFillColor(BgColorByScreeningStatus[status].CGColor);
            context.SetStrokeColor(TextColorByScreeningStatus[status].CGColor);
        }

        public static void SetScreeningColor(Screening screening, CGContext context, bool textMode)
        {
            var status = screening.Status;
            if (textMode)
            {
                context.SetFillColor(TextColorByScreeningStatus[status].CGColor);
                context.SetStrokeColor(TextColorByScreeningStatus[status].CGColor);
            }
            else
            {
                SetScreeningColor(screening, context);
            }
        }

        public static void SetTicketsStatusColor(Screening screening, CGContext context)
        {
            var status = screening.TicketStatus;
            NSColor color = ColorByTicketStatus[status];
            context.SetStrokeColor(color.CGColor);
        }

        public static NSColor ClickPadBackgroundColor(bool selected, Screening screening)
        {
            bool vod = screening is OnDemandScreening;
            return clickPadColorByVodSelected[new Tuple<bool, bool>(vod, selected)];
        }

        public static NSColor ClickPadTextColor(bool selected)
        {
            return selected ? ClickPadTextColorSelected : ClickPadTextColorUnselected;
        }

        public static NSColor SoldOutColor(bool selected)
        {
            return selected ? soldOutColorSelected : soldOutColorUnselected;
        }

        public static void DrawSoldOutSymbol(CGContext g, bool selected, CGRect rect)
        {
            var path = new CGPath();
            nfloat margin = rect.Width * 3 / 16;
            nfloat side = (nfloat)Math.Min((double)rect.Height, (double)rect.Width) - 2 * margin;
            g.SetLineWidth(2);
            SoldOutColor(selected).SetStroke();
            var diagonalLeftTopToRightBottom = new CGPath();
            diagonalLeftTopToRightBottom.AddLines(new CGPoint[]{
                new CGPoint(margin, margin + side),
                new CGPoint(margin + side, margin)
            });
            diagonalLeftTopToRightBottom.CloseSubpath();
            g.AddPath(diagonalLeftTopToRightBottom);
            var diagonalLeftBottomToRightTop = new CGPath();
            diagonalLeftBottomToRightTop.AddLines(new CGPoint[]{
                new CGPoint(margin, margin),
                new CGPoint(margin + side, margin + side)
            });
            diagonalLeftBottomToRightTop.CloseSubpath();
            g.AddPath(diagonalLeftBottomToRightTop);
            g.DrawPath(CGPathDrawingMode.Stroke);
        }

        public static void DrawTicketAvalabilityFrame(CGContext g, Screening screening, CGRect rect)
        {
            g.SetLineWidth(2);
            SetTicketsStatusColor(screening, g);
            var rectPath = new CGPath();
            nfloat org = 1;
            nfloat x = rect.Width - 2 * org;
            nfloat y = rect.Height - 2 * org;
            rectPath.AddLines(new CGPoint[]{
                new CGPoint(org, y),
                new CGPoint(x, y),
                new CGPoint(x, org),
                new CGPoint(org, org)
            });
            rectPath.CloseSubpath();
            g.AddPath(rectPath);
            g.DrawPath(CGPathDrawingMode.Stroke);
        }

        public static void DrawTicketAvalabilityFrame(CGContext g, Screening screening, nfloat side)
        {
            DrawTicketAvalabilityFrame(g, screening, new CGRect(0, 0, side, side));
        }
        #endregion
    }
}
