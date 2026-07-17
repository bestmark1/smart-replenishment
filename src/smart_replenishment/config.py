import os

import yaml


class Config:
    def __init__(self, config_path="configs/base.yaml"):
        # Make config loading robust by finding absolute paths
        if not os.path.exists(config_path):
            # Try to resolve relative to package root
            pkg_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            config_path = os.path.join(pkg_root, "configs", "base.yaml")

        with open(config_path, "r", encoding="utf-8") as f:
            self._cfg = yaml.safe_load(f)

        self.zenodo_zip_url = self._cfg["data"]["zenodo_zip_url"]
        self.raw_dir = self._cfg["data"]["raw_dir"]
        self.db_path = self._cfg["data"]["db_path"]
        self.state_id = self._cfg["data"]["state_id"]
        self.cat_id = self._cfg["data"]["cat_id"]

        self.val_folds = int(self._cfg["modeling"]["val_folds"])
        self.horizon = int(self._cfg["modeling"]["horizon"])
        self.seed = int(self._cfg["modeling"]["seed"])

        self.review_period = int(self._cfg["inventory"]["review_period"])
        self.lead_time = int(self._cfg["inventory"]["lead_time"])
        self.holding_cost = float(self._cfg["inventory"]["holding_cost"])
        self.stockout_penalty = float(self._cfg["inventory"]["stockout_penalty"])
        self.initial_stock = int(self._cfg["inventory"]["initial_stock"])
