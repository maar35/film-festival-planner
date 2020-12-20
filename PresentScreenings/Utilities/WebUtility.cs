using System;
using System.Collections.Generic;
using System.Text.RegularExpressions;

namespace PresentScreenings.TableView
{
    public static class WebUtility
    {
        #region Public Members
        public enum MediumCategory
        {
            Films,
            CombinedProgrammes,
            Events
        }
        #endregion

        #region Properties
        static public Dictionary<MediumCategory, string> FolderByCategory;
        #endregion

        #region Constructors
        static WebUtility()
        {
            FolderByCategory = new Dictionary<MediumCategory, string> { };
            FolderByCategory[MediumCategory.Films] = "films";
            FolderByCategory[MediumCategory.CombinedProgrammes] = "verzamelprogrammas";
            FolderByCategory[MediumCategory.Events] = "events";
        }
        #endregion

        #region Public Methods

        /// <summary>
        /// Html to plain text.
        /// By Ben Anderson (https://stackoverflow.com/questions/286813/how-do-you-convert-html-to-plain-text)
        /// </summary>
        /// <returns>The plain text.</returns>
        /// <param name="html">Html.</param>
        public static string HtmlToPlainText(string html)
        {
            const string tagWhiteSpace = @"(>|$)(\W|\n|\r)+<";//matches one or more (white space or line breaks) between '>' and '<'
            const string stripFormatting = @"<[^>]*(>|$)";//match any character between '<' and '>', even when end tag is missing
            const string lineBreak = @"<(br|BR)\s{0,1}\/{0,1}>";//matches: <br>,<br/>,<br />,<BR>,<BR/>,<BR />
            var lineBreakRegex = new Regex(lineBreak, RegexOptions.Multiline);
            var stripFormattingRegex = new Regex(stripFormatting, RegexOptions.Multiline);
            var tagWhiteSpaceRegex = new Regex(tagWhiteSpace, RegexOptions.Multiline);

            var text = html;
            //Decode html specific characters
            text = System.Net.WebUtility.HtmlDecode(text);
            //Remove tag whitespace/line breaks
            text = tagWhiteSpaceRegex.Replace(text, "><");
            //Replace <br /> with line breaks
            text = lineBreakRegex.Replace(text, Environment.NewLine);
            //Strip formatting
            text = stripFormattingRegex.Replace(text, string.Empty);

            return text;
        }

        public static string HtmlToText(string html)
        {
            return Screening.HtmlDecode(HtmlToPlainText(html));
        }

        public static string UrlString(string title, MediumCategory category)
        {
            string baseUrl = "https://iffr.com/nl/" + AppDelegate.FestivalYear + "/" + FolderByCategory[category] + "/";
            var quotes = @"['`""]";
            var disposables = @"[./()?]";
            var strippables = @"(" + quotes + @"+\s*)|" + disposables + @"+";
            var reStrip = new Regex(strippables, RegexOptions.CultureInvariant);
            var strippedTitle = reStrip.Replace(title.ToLowerInvariant(), "");
            var extraWordChars = @"[–★]";
            var nonWords = @"[\W-" + extraWordChars + "]+";
            var reReplace = new Regex(nonWords, RegexOptions.CultureInvariant); // space or connector punctuation.
            var result = baseUrl + reReplace.Replace(strippedTitle, "-");
            return result;
        }
        #endregion
    }
}
