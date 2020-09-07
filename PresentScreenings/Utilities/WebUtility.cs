using System;
using System.Collections.Generic;
using System.IO;
using System.Net;
using System.Text;
using System.Text.RegularExpressions;

namespace PresentScreenings.TableView
{
    public static class WebUtility
    {
        #region Public Members
        public enum MediumCatagory
        {
            Films,
            CombinedProgrammes,
            Events
        }

        public enum ParseInfoType
        {
            Description,
            Article,
            ScreenedFilms
        }
        #endregion

        #region Private Variables
        struct ParseInfo
        {
            public ParseInfoType type;
            public string description;
            public Regex re;
            public Regex filterRe;
            public string filterReplacement;
        }
        static Dictionary<MediumCatagory, List<ParseInfo>> _parseInfoByCatagory;
        #endregion

        #region Properties
        static public Dictionary<MediumCatagory, string> FolderByCatagory;
        #endregion

        #region Constructors
        static WebUtility()
        {
            FolderByCatagory = new Dictionary<MediumCatagory, string> { };
            FolderByCatagory[MediumCatagory.Films] = "films";
            FolderByCatagory[MediumCatagory.CombinedProgrammes] = "verzamelprogrammas";
            FolderByCatagory[MediumCatagory.Events] = "events";
            var descriptionParseInfo = new ParseInfo
            {
                type = ParseInfoType.Description,
                description = "Description",
                re = new Regex(@"\<meta name=""description"" content=""(.*)"" />")
            };
            var articleParseInfo = new ParseInfo
            {
                type = ParseInfoType.Article,
                description = "Article",
                re = new Regex(@"\<article.*?(\<p\>.*\</p\>)\s*\</div\>", RegexOptions.Singleline)
            };
            var screenedFilmsParseInfo = new ParseInfo
            {
                type = ParseInfoType.ScreenedFilms,
                description = "Screened films",
                re = new Regex(@"\<section class=""rectangle-column""\>\s*\<h2\>(.*?)\</h2\>\s*\<span class=""hover-info""\>.*?\<p class=""full-text""\>(.*?)\</p\>", RegexOptions.Singleline),
                filterRe = new Regex(@"^(.*)(\<main.*\</main\>)(.*)$", RegexOptions.Singleline),
                filterReplacement = @"$2"
            };
            _parseInfoByCatagory = new Dictionary<MediumCatagory, List<ParseInfo>> { };
            _parseInfoByCatagory[MediumCatagory.Films] = new List<ParseInfo> { descriptionParseInfo, articleParseInfo };
            _parseInfoByCatagory[MediumCatagory.Events] = new List<ParseInfo> { articleParseInfo };
            _parseInfoByCatagory[MediumCatagory.CombinedProgrammes] = new List<ParseInfo> { articleParseInfo, screenedFilmsParseInfo };
        }
        #endregion

        #region Private Methods
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

        public static string UrlString(string title, MediumCatagory catagory)
        {
            string baseUrl = "https://iffr.com/nl/" + AppDelegate.FestivalYear + "/" + FolderByCatagory[catagory] + "/";
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

        public static FilmInfo TryParseUrlSummary(HttpWebRequest request, string url, MediumCatagory catagory, int filmId)
        {
            var response = request.GetResponse() as HttpWebResponse;
            var stream = new StreamReader(response.GetResponseStream());
            var text = stream.ReadToEnd();
            stream.Close();
            var builder = new StringBuilder();
            var allParsesFailed = false;
            var filmDescription = string.Empty;
            var article = string.Empty;
            var ScreenedFileDescriptionByTitle = new Dictionary<string, string> { };
            foreach (var parseInfo in _parseInfoByCatagory[catagory])
            {
                var success = false;
                if (parseInfo.filterRe != null && parseInfo.filterReplacement != null)
                {
                    text = parseInfo.filterRe.Replace(text, parseInfo.filterReplacement);
                }
                foreach (Match match in parseInfo.re.Matches(text))
                {
                    //builder.AppendFormat($"-match-at-{match.Index}-->\n");
                    var groupCount = match.Groups.Count;
                    string screenedFilmTitle = string.Empty;
                    for (int groupNumber = 1; groupNumber < groupCount; groupNumber++)
                    {
                        //builder.AppendFormat($"-group-{groupNumber}-->\n");
                        var textUnit = match.Groups[groupNumber].Value;
                        switch (parseInfo.type)
                        {
                            case ParseInfoType.Description:
                                filmDescription = textUnit;
                                break;
                            case ParseInfoType.Article:
                                article = textUnit;
                                break;
                            case ParseInfoType.ScreenedFilms:
                                if (groupNumber % 2 == 1)
                                {
                                    screenedFilmTitle = textUnit;
                                }
                                else
                                {
                                    ScreenedFileDescriptionByTitle[screenedFilmTitle] = textUnit;
                                }
                                break;
                        }
                    }
                    success = true;
                }
                if (!success)
                {
                    allParsesFailed = true;
                }
            }
            if (allParsesFailed)
            {
                builder.AppendLine($"URL {url} could not be parsed.");
                builder.AppendLine("===");
                builder.Append(text);
                throw new UnparseblePageException(builder.ToString());
            }
            var info = new FilmInfo(filmId, Film.FilmInfoStatus.Complete, filmDescription, article);
            foreach (string title in ScreenedFileDescriptionByTitle.Keys)
            {
                info.AddScreenedFilm(title, ScreenedFileDescriptionByTitle[title]);
            }
            return info;
        }
        #endregion
    }
}
