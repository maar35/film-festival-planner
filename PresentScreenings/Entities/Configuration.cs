using System.Collections.Generic;

namespace PresentScreenings.TableView
{
    public class Configuration
    {
        #region Properties
        public Dictionary<string, string> Constants { get; private set; }
        public Dictionary<string, string> Paths { get; private set; }
        #endregion

        #region Constructors
        public Configuration()
        {
        }
        #endregion
    }
}
