import json
import logging
import subprocess
import sys
from pathlib import Path


class ModelSetup:
    def __init__(self):
        self.models_config = {
            "spacy": {
                "models": ["en_core_web_lg", "en_core_web_sm"],
                "preferred": "en_core_web_lg",
                "fallback": "en_core_web_sm",
                "installed": False,
            },
            "transformers": {
                "models": [
                    "bert-base-uncased",  # For tokenizer
                    "facebook/bart-large-mnli",  # For zero-shot classification
                ],
                "installed": False,
            },
            "sentence_transformers": {
                "models": ["all-MiniLM-L6-v2"],
                "installed": False,
            },
        }

        # Create models directory if it doesn't exist
        self.models_dir = Path("models")
        self.models_dir.mkdir(exist_ok=True)

        # State file to track installation status
        self.state_file = self.models_dir / "installation_state.json"

    def check_pip_packages(self) -> bool:
        """Check if required packages are installed"""
        logging.info({"action": "checking_pip_packages"})

        required_packages = [
            "spacy",
            "transformers",
            "sentence-transformers",
            "scikit-learn",
            "numpy",
            "textstat",
            "torch",
            "fastapi",
            "uvicorn",
        ]

        try:
            import pkg_resources

            installed_packages = [pkg.key for pkg in pkg_resources.working_set]

            missing_packages = [
                pkg
                for pkg in required_packages
                if pkg.lower() not in installed_packages
            ]

            if missing_packages:
                logging.error(
                    {
                        "action": "package_check_failed",
                        "missing_packages": missing_packages,
                    }
                )
                return False

            logging.info(
                {
                    "action": "package_check_successful",
                    "status": "all_packages_installed",
                }
            )
            return True

        except Exception as e:
            logging.error(
                {
                    "action": "package_check_failed",
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
            )
            return False

    def install_pip_packages(self):
        """Install required pip packages"""
        logging.info({"action": "installing_pip_packages"})

        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"]
            )
            logging.info(
                {
                    "action": "pip_installation_successful",
                    "status": "packages_installed",
                }
            )
        except subprocess.CalledProcessError as e:
            logging.error(
                {
                    "action": "pip_installation_failed",
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
            )
            raise

    def check_spacy_model(self, model_name: str) -> bool:
        """Check if a specific spaCy model is installed"""
        try:
            import spacy

            spacy.load(model_name)
            return True
        except OSError:
            return False

    def install_spacy_models(self):
        """Install spaCy models"""
        logging.info({"action": "installing_spacy_models"})

        try:
            # Try to install preferred model first
            preferred_model = self.models_config["spacy"]["preferred"]
            try:
                if not self.check_spacy_model(preferred_model):
                    logging.info(
                        {"action": "installing_spacy_model", "model": preferred_model}
                    )
                    subprocess.check_call(
                        [sys.executable, "-m", "spacy", "download", preferred_model]
                    )
                self.models_config["spacy"]["installed"] = True
            except subprocess.CalledProcessError:
                logging.warning(
                    {
                        "action": "preferred_model_installation_failed",
                        "model": preferred_model,
                    }
                )

                # Try fallback model
                fallback_model = self.models_config["spacy"]["fallback"]
                if not self.check_spacy_model(fallback_model):
                    logging.info(
                        {"action": "installing_spacy_model", "model": fallback_model}
                    )
                    subprocess.check_call(
                        [sys.executable, "-m", "spacy", "download", fallback_model]
                    )
                self.models_config["spacy"]["installed"] = True

            logging.info({"action": "spacy_installation_complete", "status": "success"})

        except Exception as e:
            logging.error(
                {
                    "action": "spacy_installation_failed",
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
            )
            raise

    def download_transformer_models(self):
        """Download transformer models"""
        logging.info({"action": "downloading_transformer_models"})

        try:
            from transformers import AutoModel, AutoTokenizer

            for model_name in self.models_config["transformers"]["models"]:
                logging.info(
                    {"action": "downloading_transformer_model", "model": model_name}
                )
                AutoTokenizer.from_pretrained(model_name)
                AutoModel.from_pretrained(model_name)

            self.models_config["transformers"]["installed"] = True
            logging.info(
                {"action": "transformer_download_complete", "status": "success"}
            )

        except Exception as e:
            logging.error(
                {
                    "action": "transformer_download_failed",
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
            )
            raise

    def download_sentence_transformer_models(self):
        """Download sentence transformer models"""
        logging.info({"action": "downloading_sentence_transformer_models"})

        try:
            from sentence_transformers import SentenceTransformer

            for model_name in self.models_config["sentence_transformers"]["models"]:
                logging.info(
                    {"action": "downloading_sentence_transformer", "model": model_name}
                )
                SentenceTransformer(model_name)

            self.models_config["sentence_transformers"]["installed"] = True
            logging.info(
                {
                    "action": "sentence_transformer_download_complete",
                    "status": "success",
                }
            )

        except Exception as e:
            logging.error(
                {
                    "action": "sentence_transformer_download_failed",
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
            )
            raise

    def save_state(self):
        """Save installation state to file"""
        try:
            with open(self.state_file, "w") as f:
                json.dump(self.models_config, f, indent=2)
            logging.info(
                {"action": "state_save_successful", "file": str(self.state_file)}
            )
        except Exception as e:
            logging.error(
                {
                    "action": "state_save_failed",
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
            )

    def load_state(self) -> bool:
        """Load installation state from file"""
        try:
            if self.state_file.exists():
                with open(self.state_file, "r") as f:
                    self.models_config = json.load(f)
                logging.info(
                    {"action": "state_load_successful", "file": str(self.state_file)}
                )
                return True
        except Exception as e:
            logging.error(
                {
                    "action": "state_load_failed",
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
            )
        return False

    def setup(self):
        """Main setup function to install all required models"""
        logging.info({"action": "starting_model_setup"})

        try:
            # Check if we have a saved state
            if self.load_state():
                logging.info(
                    {
                        "action": "checking_existing_installation",
                        "status": "found_previous_state",
                    }
                )

            # Check and install pip packages
            if not self.check_pip_packages():
                self.install_pip_packages()

            # Install/download models
            if not self.models_config["spacy"]["installed"]:
                self.install_spacy_models()

            if not self.models_config["transformers"]["installed"]:
                self.download_transformer_models()

            if not self.models_config["sentence_transformers"]["installed"]:
                self.download_sentence_transformer_models()

            # Save final state
            self.save_state()

            logging.info({"action": "model_setup_complete", "status": "success"})

        except Exception as e:
            logging.error(
                {
                    "action": "model_setup_failed",
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
            )
            raise


if __name__ == "__main__":
    setup = ModelSetup()
    setup.setup()
